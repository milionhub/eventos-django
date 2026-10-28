import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { vi } from 'vitest';

import { Member, RoleEnum } from '../../../core/api/models';
import { AuthService } from '../../../core/auth/auth.service';
import { Members } from './members';

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));
const URL = '/api/v1/organizations/sala-apolo/members/';

const member = (id: number, role: RoleEnum, first_name: string): Member => ({
  id,
  role,
  created_at: '2026-10-28T10:00:00Z',
  user: {
    id: id * 10,
    email: `${first_name.toLowerCase()}@example.com`,
    first_name,
    last_name: '',
  },
});

describe('Members', () => {
  let fixture: ComponentFixture<Members>;
  let http: HttpTestingController;
  let myRole: RoleEnum | null;
  const reloadUser = vi.fn();

  beforeEach(async () => {
    myRole = 'OWNER';
    reloadUser.mockReset().mockResolvedValue(undefined);
    await TestBed.configureTestingModule({
      imports: [Members],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: AuthService,
          useValue: { user: signal({ id: 10 }), reloadUser, roleIn: () => myRole },
        },
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Members);
    fixture.componentRef.setInput('org', 'sala-apolo');
    fixture.detectChanges();
    await flushMicrotasks();
    http.expectOne(URL).flush([member(1, 'OWNER', 'Ana'), member(2, 'STAFF', 'Luis')]);
    await fixture.whenStable();
  });

  afterEach(() => http.verify());

  const element = () => fixture.nativeElement as HTMLElement;
  const component = () => fixture.componentInstance as unknown as Record<string, CallableFunction>;
  const rows = () => element().querySelectorAll('li.member');

  async function settle(): Promise<void> {
    await flushMicrotasks();
    await fixture.whenStable();
  }

  it('lists members and marks me', () => {
    expect(rows()).toHaveLength(2);
    expect(rows()[0].textContent).toContain('Tú');
    expect(rows()[1].textContent).not.toContain('Tú');
  });

  it('adds a member by email', async () => {
    const email = element().querySelector<HTMLInputElement>('input[formcontrolname="email"]')!;
    email.value = 'marta@example.com';
    email.dispatchEvent(new Event('input'));
    element().querySelector('form')!.dispatchEvent(new Event('submit'));

    const req = http.expectOne(URL);
    expect(req.request.body).toEqual({ email: 'marta@example.com', role: 'STAFF' });
    req.flush(member(3, 'STAFF', 'Marta'), { status: 201, statusText: 'Created' });
    await settle();

    expect(rows()).toHaveLength(3);
    expect(element().querySelector('[role="status"]')?.textContent).toContain('Marta se ha unido');
  });

  it('shows the business reason when a member cannot be added', async () => {
    const email = element().querySelector<HTMLInputElement>('input[formcontrolname="email"]')!;
    email.value = 'nadie@example.com';
    email.dispatchEvent(new Event('input'));
    element().querySelector('form')!.dispatchEvent(new Event('submit'));

    http
      .expectOne(URL)
      .flush(
        { code: 'user_not_registered', detail: 'No hay ninguna cuenta con ese email.' },
        { status: 400, statusText: 'Bad Request' },
      );
    await settle();

    expect(element().querySelector('[role="alert"]')?.textContent).toContain(
      'No hay ninguna cuenta con ese email.',
    );
  });

  it('changes a role', async () => {
    const source = { value: 'MANAGER' };
    component()['changeRole'](member(2, 'STAFF', 'Luis'), { value: 'MANAGER', source });

    const req = http.expectOne(`${URL}2/`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ role: 'MANAGER' });
    req.flush(member(2, 'MANAGER', 'Luis'));
    await settle();

    expect(element().querySelector('[role="status"]')?.textContent).toContain(
      'Luis ahora es Gestor',
    );
  });

  it('undoes the selection when the last owner tries to step down', async () => {
    const source = { value: 'MANAGER' };
    component()['changeRole'](member(1, 'OWNER', 'Ana'), { value: 'MANAGER', source });

    http
      .expectOne(`${URL}1/`)
      .flush(
        { code: 'last_owner', detail: 'La organización debe tener al menos un propietario.' },
        { status: 409, statusText: 'Conflict' },
      );
    await settle();

    expect(source.value).toBe('OWNER');
    expect(element().querySelector('[role="alert"]')?.textContent).toContain(
      'al menos un propietario',
    );
  });

  it('asks for confirmation before removing', async () => {
    const remove = rows()[1].querySelector<HTMLButtonElement>('button.remove')!;

    remove.click();
    await fixture.whenStable();
    http.expectNone(`${URL}2/`);
    expect(remove.textContent).toContain('¿Seguro?');

    remove.click();
    http.expectOne(`${URL}2/`).flush(null, { status: 204, statusText: 'No Content' });
    await settle();

    expect(rows()).toHaveLength(1);
  });

  it('leaves the page after I stop being an owner', async () => {
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    myRole = 'MANAGER';

    component()['changeRole'](member(1, 'OWNER', 'Ana'), { value: 'MANAGER', source: {} });
    http.expectOne(`${URL}1/`).flush(member(1, 'MANAGER', 'Ana'));
    await settle();

    expect(reloadUser).toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith(['/org', 'sala-apolo']);
  });
});
