import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { RoleEnum } from '../../../core/api/models';
import { Organization } from './organization';

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));

describe('Organization', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Organization],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  async function render(role: RoleEnum): Promise<HTMLElement> {
    const fixture = TestBed.createComponent(Organization);
    fixture.componentRef.setInput('org', 'sala-apolo');
    fixture.detectChanges();
    await flushMicrotasks();
    http.expectOne('/api/v1/organizations/sala-apolo/').flush({
      role,
      organization: {
        id: 1,
        name: 'Sala Apolo',
        slug: 'sala-apolo',
        description: '',
        created_at: '2026-10-28T10:00:00Z',
      },
    });
    await fixture.whenStable();
    return fixture.nativeElement;
  }

  it('shows the organization and my role', async () => {
    const element = await render('MANAGER');

    expect(element.querySelector('h1')?.textContent).toContain('Sala Apolo');
    expect(element.textContent).toContain('Gestor');
  });

  it('links owners to member management', async () => {
    const link = (await render('OWNER')).querySelector('a[href="/org/sala-apolo/members"]');

    expect(link).toBeTruthy();
  });

  it('hides member management from other roles', async () => {
    const link = (await render('STAFF')).querySelector('a[href="/org/sala-apolo/members"]');

    expect(link).toBeNull();
  });
});
