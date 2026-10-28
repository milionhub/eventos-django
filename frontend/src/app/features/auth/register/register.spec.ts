import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { vi } from 'vitest';

import { AuthService } from '../../../core/auth/auth.service';
import { Register } from './register';

describe('Register', () => {
  let fixture: ComponentFixture<Register>;
  let element: HTMLElement;
  const register = vi.fn();

  beforeEach(async () => {
    register.mockReset();
    await TestBed.configureTestingModule({
      imports: [Register],
      providers: [provideRouter([]), { provide: AuthService, useValue: { register } }],
    }).compileComponents();
    fixture = TestBed.createComponent(Register);
    element = fixture.nativeElement;
    await fixture.whenStable();
  });

  function input(name: string): HTMLInputElement {
    return element.querySelector(`input[formcontrolname="${name}"]`)!;
  }

  async function submit(values: Record<string, string>): Promise<void> {
    for (const [name, value] of Object.entries(values)) {
      input(name).value = value;
      input(name).dispatchEvent(new Event('input'));
    }
    element.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
  }

  const valid = { first_name: 'Ana', email: 'ana@example.com', password: 'Concierto-2026' };

  it('creates the account and goes home', async () => {
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    register.mockResolvedValue({});

    await submit(valid);

    expect(register).toHaveBeenCalledWith({ ...valid, last_name: '' });
    expect(navigate).toHaveBeenCalledWith('/');
  });

  it('checks the password length before calling the API', async () => {
    await submit({ ...valid, password: 'short' });

    expect(register).not.toHaveBeenCalled();
    expect(element.textContent).toContain('al menos 8 caracteres');
  });

  it('marks the email as taken on 409', async () => {
    register.mockRejectedValue(new HttpErrorResponse({ status: 409 }));

    await submit(valid);

    expect(element.textContent).toContain('Ya existe una cuenta con este email.');
  });

  it("shows Django's password validation message on the field", async () => {
    register.mockRejectedValue(
      new HttpErrorResponse({
        status: 400,
        error: { password: ['Esta contraseña es demasiado común.'] },
      }),
    );

    await submit(valid);

    expect(element.textContent).toContain('Esta contraseña es demasiado común.');
  });
});
