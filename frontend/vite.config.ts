import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { VantResolver } from '@vant/auto-import-resolver'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { fileURLToPath, URL } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
// variables.scss 绝对路径（正斜杠，sass 兼容）
const varsPath = resolve(__dirname, 'src/styles/variables.scss').replace(/\\/g, '/')

export default defineConfig({
  plugins: [
    vue(),
    Components({
      resolvers: [VantResolver(), ElementPlusResolver()],
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true, // 端口被占直接报错，不偷偷换端口
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        // 用函数形式注入变量，排除 variables.scss 自身避免循环引用
        additionalData: (source: string, fp: string) => {
          if (fp.replace(/\\/g, '/').endsWith('src/styles/variables.scss')) {
            return source
          }
          return `@use '${varsPath}' as *;\n${source}`
        },
      },
    },
  },
})
