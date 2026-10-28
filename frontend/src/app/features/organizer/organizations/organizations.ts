import { Component, inject, resource, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router, RouterLink } from '@angular/router';

import { Api } from '../../../core/api/api';
import { organizationsCreate, organizationsList } from '../../../core/api/functions';
import { AuthService } from '../../../core/auth/auth.service';
import { ROLE_LABELS } from '../../../shared/roles';

/** "My organizations": the ones I belong to, and the form to create a new one. */
@Component({
  selector: 'app-organizations',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './organizations.html',
  styleUrl: './organizations.scss',
})
export class Organizations {
  private readonly api = inject(Api);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly roleLabels = ROLE_LABELS;
  protected readonly organizations = resource({
    loader: () => this.api.invoke(organizationsList),
  });

  protected readonly creating = signal(false);
  protected readonly submitting = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly form = inject(NonNullableFormBuilder).group({
    name: ['', [Validators.required, Validators.maxLength(120)]],
    description: [''],
  });

  protected toggleForm(): void {
    this.creating.update((open) => !open);
    this.error.set(null);
  }

  protected async create(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitting.set(true);
    this.error.set(null);
    try {
      const created = await this.api.invoke(organizationsCreate, {
        body: this.form.getRawValue(),
      });
      await this.auth.reloadUser(); // the new OWNER membership
      await this.router.navigate(['/org', created.organization.slug]);
    } catch {
      this.error.set('No se ha podido crear la organización. Inténtalo de nuevo.');
    } finally {
      this.submitting.set(false);
    }
  }
}
