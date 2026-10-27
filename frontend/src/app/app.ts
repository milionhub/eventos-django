import { Component } from '@angular/core';

import { Shell } from './core/layout/shell/shell';

@Component({
  selector: 'app-root',
  imports: [Shell],
  template: '<app-shell />',
})
export class App {}
