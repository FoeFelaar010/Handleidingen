import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
// base './' = werkt zowel op github.io/handleidingen/ als op een eigen domein
// __BOUW__ zit achter elke data-url, zodat de browser na een nieuwe upload geen oude handleiding toont
export default defineConfig({
  plugins: [react()],
  base: './',
  define: { __BOUW__: JSON.stringify(String(Date.now())) },
})
