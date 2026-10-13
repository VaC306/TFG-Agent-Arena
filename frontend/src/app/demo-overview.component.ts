import { Component, output } from '@angular/core';
// No showcase content or static data access is compiled into the backend UI.
@Component({selector:'arena-demo-overview',standalone:true,template:''})
export class DemoOverviewComponent { opened = output<string>(); }
