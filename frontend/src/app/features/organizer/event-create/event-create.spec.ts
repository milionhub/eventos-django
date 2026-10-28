import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { EventCreate } from './event-create';

describe('EventCreate', () => {
  let fixture: ComponentFixture<EventCreate>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventCreate],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: AuthService,
          useValue: {
            user: signal({
              memberships: [
                { organization_slug: 'sala-apolo', organization_name: 'Sala Apolo', role: 'OWNER' },
              ],
            }),
          },
        },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(EventCreate);
    fixture.componentRef.setInput('org', 'sala-apolo');
    await fixture.whenStable();
  });

  it('previews the public card while the form is filled in', async () => {
    const element = fixture.nativeElement as HTMLElement;
    const preview = () => element.querySelector('aside app-event-ticket')!.textContent!;
    expect(preview()).toContain('Título del evento');
    expect(preview()).toContain('Sala Apolo');

    const title = element.querySelector<HTMLInputElement>('input[formcontrolname="title"]')!;
    title.value = 'Noche de Jazz';
    title.dispatchEvent(new Event('input'));
    await fixture.whenStable();

    expect(preview()).toContain('Noche de Jazz');
    expect(preview()).toContain('100 plazas libres');
  });
});
