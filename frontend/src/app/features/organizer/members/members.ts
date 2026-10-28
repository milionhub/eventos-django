import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, input, resource, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectChange, MatSelectModule } from '@angular/material/select';
import { Router, RouterLink } from '@angular/router';

import { Api } from '../../../core/api/api';
import {
  membersCreate,
  membersDestroy,
  membersList,
  membersUpdate,
} from '../../../core/api/functions';
import { Member, RoleEnum } from '../../../core/api/models';
import { AuthService } from '../../../core/auth/auth.service';
import { initials, ROLE_LABELS, ROLES } from '../../../shared/roles';

interface Notice {
  kind: 'success' | 'error';
  text: string;
}

/** Business errors come back as `{code, detail}` with a message meant for the user. */
function errorText(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    if (error.error?.code && error.error?.detail) return error.error.detail;
    if (error.status === 403 || error.status === 404) {
      return 'Ya no tienes permiso para gestionar esta organización.';
    }
  }
  return 'No se ha podido completar la acción. Inténtalo de nuevo.';
}

const displayName = (member: Member) =>
  `${member.user.first_name} ${member.user.last_name}`.trim() || member.user.email;

/** RN-05: the OWNER adds members by email, changes their role or removes them. */
@Component({
  selector: 'app-members',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
  ],
  templateUrl: './members.html',
  styleUrl: './members.scss',
})
export class Members {
  private readonly api = inject(Api);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  /** `:org` route parameter. */
  readonly org = input.required<string>();

  protected readonly roles = ROLES;
  protected readonly roleLabels = ROLE_LABELS;
  protected readonly initials = initials;
  protected readonly displayName = displayName;
  protected readonly myId = computed(() => this.auth.user()?.id);

  protected readonly members = resource({
    params: () => ({ org_slug: this.org() }),
    loader: ({ params }) => this.api.invoke(membersList, params),
  });

  protected readonly notice = signal<Notice | null>(null);
  protected readonly adding = signal(false);
  protected readonly busyId = signal<number | null>(null);
  protected readonly confirmingId = signal<number | null>(null);

  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly form = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    role: this.fb.control<RoleEnum>('STAFF'),
  });

  protected async add(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.adding.set(true);
    this.notice.set(null);
    try {
      const member = await this.api.invoke(membersCreate, {
        org_slug: this.org(),
        body: this.form.getRawValue(),
      });
      this.members.update((list) => [...(list ?? []), member]);
      this.form.reset({ email: '', role: 'STAFF' });
      this.notify(
        'success',
        `${displayName(member)} se ha unido como ${ROLE_LABELS[member.role]}.`,
      );
    } catch (error) {
      this.notify('error', errorText(error));
    } finally {
      this.adding.set(false);
    }
  }

  protected async changeRole(member: Member, change: MatSelectChange<RoleEnum>): Promise<void> {
    this.busyId.set(member.id);
    this.notice.set(null);
    try {
      const updated = await this.api.invoke(membersUpdate, {
        org_slug: this.org(),
        member_id: member.id,
        body: { role: change.value },
      });
      this.replace(updated);
      this.notify('success', `${displayName(updated)} ahora es ${ROLE_LABELS[updated.role]}.`);
      if (updated.user.id === this.myId()) await this.afterChangingMyself();
    } catch (error) {
      change.source.value = member.role; // undo the selection: nothing changed on the server
      this.notify('error', errorText(error));
    } finally {
      this.busyId.set(null);
    }
  }

  /** First click asks for confirmation; the second one removes. */
  protected async remove(member: Member): Promise<void> {
    if (this.confirmingId() !== member.id) {
      this.confirmingId.set(member.id);
      return;
    }
    this.confirmingId.set(null);
    this.busyId.set(member.id);
    this.notice.set(null);
    try {
      await this.api.invoke(membersDestroy, { org_slug: this.org(), member_id: member.id });
      this.members.update((list) => list?.filter((m) => m.id !== member.id));
      this.notify('success', `${displayName(member)} ya no es miembro.`);
      if (member.user.id === this.myId()) await this.afterChangingMyself();
    } catch (error) {
      this.notify('error', errorText(error));
    } finally {
      this.busyId.set(null);
    }
  }

  private replace(updated: Member): void {
    this.members.update((list) => list?.map((m) => (m.id === updated.id ? updated : m)));
  }

  private notify(kind: Notice['kind'], text: string): void {
    this.notice.set({ kind, text });
  }

  /** After stepping down or leaving, this page may no longer be ours to see. */
  private async afterChangingMyself(): Promise<void> {
    await this.auth.reloadUser();
    if (this.auth.roleIn(this.org()) !== 'OWNER') {
      await this.router.navigate(['/org', this.org()]);
    }
  }
}
