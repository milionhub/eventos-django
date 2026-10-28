import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { vi } from 'vitest';

import { MyOrganization } from '../../../core/api/models';
import { AuthService } from '../../../core/auth/auth.service';
import { Organizations } from './organizations';

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));

const apolo: MyOrganization = {
  role: 'MANAGER',
  organization: {
    id: 1,
    name: 'Sala Apolo',
    slug: 'sala-apolo',
    description: 'Conciertos en Barcelona',
    created_at: '2026-10-28T10:00:00Z',
  },
};

describe('Organizations', () => {
  let fixture: ComponentFixture<Organizations>;
  let http: HttpTestingController;
  const reloadUser = vi.fn();

  beforeEach(async () => {
    reloadUser.mockReset().mockResolvedValue(undefined);
    await TestBed.configureTestingModule({
      imports: [Organizations],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { reloadUser } },
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Organizations);
    fixture.detectChanges();
    await flushMicrotasks();
  });

  afterEach(() => http.verify());

  const element = () => fixture.nativeElement as HTMLElement;

  async function respondWith(list: MyOrganization[]): Promise<void> {
    http.expectOne('/api/v1/organizations/').flush(list);
    await fixture.whenStable();
  }

  it('lists my organizations with my role in each', async () => {
    await respondWith([apolo]);

    const card = element().querySelector('a.org')!;
    expect(card.getAttribute('href')).toBe('/org/sala-apolo');
    expect(card.textContent).toContain('Sala Apolo');
    expect(card.textContent).toContain('Gestor');
  });

  it('explains what to do when the user has no organizations', async () => {
    await respondWith([]);

    expect(element().textContent).toContain('Aún no formas parte de ninguna organización');
  });

  it('previews the address the organization will get', async () => {
    await respondWith([]);
    (element().querySelector('button.new') as HTMLButtonElement).click();
    await fixture.whenStable();

    const name = element().querySelector<HTMLInputElement>('input[formcontrolname="name"]')!;
    name.value = 'Peña Flamenca Ñandú';
    name.dispatchEvent(new Event('input'));
    await fixture.whenStable();

    expect(element().textContent).toContain('/org/pena-flamenca-nandu');
  });

  it('creates an organization and opens it', async () => {
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    await respondWith([]);

    (element().querySelector('button.new') as HTMLButtonElement).click();
    await fixture.whenStable();
    const name = element().querySelector<HTMLInputElement>('input[formcontrolname="name"]')!;
    name.value = 'Sala Apolo';
    name.dispatchEvent(new Event('input'));
    element().querySelector('form')!.dispatchEvent(new Event('submit'));

    const req = http.expectOne('/api/v1/organizations/');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ name: 'Sala Apolo', description: '' });
    req.flush({ ...apolo, role: 'OWNER' }, { status: 201, statusText: 'Created' });
    await flushMicrotasks();
    await fixture.whenStable();

    expect(reloadUser).toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith(['/org', 'sala-apolo']);
  });
});
