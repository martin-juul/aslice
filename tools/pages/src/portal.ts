import '@fontsource/geist/400.css';
import '@fontsource/geist-mono/400.css';
import '@fontsource/space-grotesk/400.css';
import '../style.css';

import { mountAppearance } from './features/appearance/feature';
import { mountReader } from './features/reader/feature';

mountAppearance();
mountReader();
