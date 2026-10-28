import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { vi } from 'vitest';

import { AuthService } from '../../../core/auth/auth.service';
import { Login } from './login';

describe('Login', () => {
  let fixture: ComponentFixture<Login>;
  let element: HTMLElement;
  const login = vi.fn();

  beforeEach(async () => {
    login.mockReset();
    await TestBed.configureTestingModule({
      imports: [Login],
      providers: [provideRouter([]), { provide: AuthService, useValue: { login } }],
    }).compileComponents();
    fixture = TestBed.createComponent(Login);
    element = fixture.nativeElement;
    await fixture.whenStable();
  });

  async function submit(email = 'ana@example.com', password = 'secret'): Promise<void> {
    const [emailInput, passwordInput] = element.querySelectorAll('input');
    emailInput.value = email;
    emailInput.dispatchEvent(new Event('input'));
    passwordInput.value = password;
    passwordInput.dispatchEvent(new Event('input'));
    element.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
  }

  it('signs in and goes to the requested page', async () => {
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    fixture.componentRef.setInput('returnUrl', '/events/jazz');
    login.mockResolvedValue({});

    await submit();

    expect(login).toHaveBeenCalledWith({ email: 'ana@example.com', password: 'secret' });
    expect(navigate).toHaveBeenCalledWith('/events/jazz');
  });

  it('does not call the API while the form is invalid', async () => {
    await submit('not-an-email', '');

    expect(login).not.toHaveBeenCalled();
    expect(element.textContent).toContain('Este email no es válido.');
  });

  it('shows a clear message for wrong credentials', async () => {
    login.mockRejectedValue(new HttpErrorResponse({ status: 401 }));

    await submit();

    expect(element.querySelector('[role="alert"]')?.textContent).toContain(
      'Email o contraseña incorrectos.',
    );
  });

  it('explains when login is throttled', async () => {
    login.mockRejectedValue(new HttpErrorResponse({ status: 429 }));

    await submit();

    expect(element.querySelector('[role="alert"]')?.textContent).toContain('Demasiados intentos');
  });
});
