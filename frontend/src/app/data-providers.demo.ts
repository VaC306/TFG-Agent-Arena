import { Provider } from '@angular/core';
import { ArenaService } from './arena.service';
import { DemoArenaService } from './demo-arena.service';
export const dataProviders: Provider[] = [{provide: ArenaService, useClass: DemoArenaService}];
