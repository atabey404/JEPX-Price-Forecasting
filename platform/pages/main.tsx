import { createRoot } from 'react-dom/client';
import '../app/globals.css';
import '../app/dark.css';
import Intro from '../app/page';
import Workspace from '../app/workspace/page';

const root = document.getElementById('root')!;
createRoot(root).render(
  /\/workspace\/?$/.test(window.location.pathname) ? <Workspace /> : <Intro />
);
