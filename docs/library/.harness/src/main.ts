import 'core-js/stable';
import 'whatwg-fetch';
import '@fontsource/geist/400.css';
import '@fontsource/geist/600.css';
import '@fontsource/geist-mono/400.css';
import '@fontsource/space-grotesk/500.css';
import './style.scss';
import { app } from './app';

void app(document.getElementById('app')!);
