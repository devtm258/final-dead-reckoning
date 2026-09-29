import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';
export default defineConfig({
 plugins:[react()],
 resolve:{alias:{'@':fileURLToPath(new URL('./src',import.meta.url))}},
 server:{proxy:{'/api':'http://127.0.0.1:8000'}},
 build:{rollupOptions:{output:{manualChunks(id){if(id.includes('recharts'))return 'charts';if(id.includes('leaflet'))return 'map';}}}}
});
