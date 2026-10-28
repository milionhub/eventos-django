import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, input, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router, RouterLink } from '@angular/router';

import { safeReturnUrl } from '../../../core/auth/auth.guards';
import { AuthService } from '../../../core/auth/auth.service';

/** Mirrors Django's MinimumLengthValidator so most mistakes are caught before submitting. */
const MIN_PASSWORD_LENGTH = 8;

@Component({
  selector: 'app-register',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './register.html',
  styleUrl: '../auth-page.scss',
})
export class Register {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly returnUrl = input<string>();

  protected readonly minPasswordLength = MIN_PASSWORD_LENGTH;
  protected readonly form = inject(NonNullableFormBuilder).group({
    first_name: ['', Validators.maxLength(150)],
    last_name: ['', Validators.maxLength(150)],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(MIN_PASSWORD_LENGTH)]],
  });
  protected readonly submitting = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly hidePassword = signal(true);

  protected async submit(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitting.set(true);
    this.error.set(null);
    try {
      await this.auth.register(this.form.getRawValue());
      await this.router.navigateByUrl(safeReturnUrl(this.returnUrl() ?? null));
    } catch (error) {
      this.showError(error);
    } finally {
      this.submitting.set(false);
    }
  }

  /** Server-side rules (unique email, Django's password validators) shown on their fields. */
  private showError(error: unknown): void {
    if (error instanceof HttpErrorResponse && error.status === 409) {
      this.form.controls.email.setErrors({ taken: true });
    } else if (
      error instanceof HttpErrorResponse &&
      error.status === 400 &&
      error.error?.password
    ) {
      this.form.controls.password.setErrors({ server: error.error.password[0] });
    } else {
      this.error.set('No se ha podido crear la cuenta. Inténtalo de nuevo.');
    }
  }
}
