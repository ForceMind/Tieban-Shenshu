// 铁板神数 纯前端发布构建：算法/内联脚本混淆 + 数据/库压缩 + HTML 压缩
// 依赖: npm i terser javascript-obfuscator html-minifier-terser
// 用法: node tools/build.js   → 产物在 tools/dist/，再自行打包为 zip 部署 CF Pages
const fs = require('fs');
const path = require('path');
const obfuscator = require('javascript-obfuscator');
const { minify: terserMinify } = require('terser');
const { minify: htmlMinify } = require('html-minifier-terser');

const SRC = path.join(__dirname, '..');
const DIST = path.join(__dirname, 'dist');

function obfuscateCode(src, heavy) {
  return obfuscator.obfuscate(src, {
    compact: true,
    controlFlowFlattening: !!heavy,
    controlFlowFlatteningThreshold: heavy ? 0.5 : 0,
    deadCodeInjection: false,
    stringArray: true,
    stringArrayThreshold: 0.75,
    stringArrayEncoding: ['base64'],
    numbersToExpressions: true,
    simplify: true,
    renameGlobals: false,          // 关键：不改全局名，保证 window.* 与 onclick 引用的顶层函数可用
    identifierNamesGenerator: 'hexadecimal',
    selfDefending: false,
    transformObjectKeys: false,
  }).getObfuscatedCode();
}

async function minifyJs(src) {
  const r = await terserMinify(src, { compress: true, mangle: true });
  if (r.error) throw r.error;
  return r.code;
}

// 轻量 CSS 压缩：去注释、折叠空白、去多余符号周围空格
function minifyCss(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\s+/g, ' ')
    .replace(/\s*([{}:;,>])\s*/g, '$1')
    .replace(/;}/g, '}')
    .trim();
}

// 混淆 HTML 中所有无属性的内联 <script>（外链 <script src=...> 不匹配）
async function processHtml(html) {
  const re = /<script>([\s\S]*?)<\/script>/g;
  let out = '', last = 0, m;
  while ((m = re.exec(html)) !== null) {
    out += html.slice(last, m.index) + '<script>' + obfuscateCode(m[1], false) + '</script>';
    last = m.index + m[0].length;
  }
  out += html.slice(last);
  return htmlMinify(out, { collapseWhitespace: true, removeComments: true, minifyCSS: true, minifyJS: false });
}

async function main() {
  fs.rmSync(DIST, { recursive: true, force: true });
  fs.mkdirSync(path.join(DIST, 'js'), { recursive: true });
  fs.mkdirSync(path.join(DIST, 'css'), { recursive: true });

  // 0) 样式：压缩
  fs.writeFileSync(path.join(DIST, 'css/app.css'),
    minifyCss(fs.readFileSync(path.join(SRC, 'css/app.css'), 'utf-8')));

  // 1) 算法：完整混淆
  fs.writeFileSync(path.join(DIST, 'js/tieban.js'),
    obfuscateCode(fs.readFileSync(path.join(SRC, 'js/tieban.js'), 'utf-8'), true));

  // 2) 库 + 数据：压缩
  for (const f of ['js/lunar.js', 'js/db-data.js', 'js/duanyu-modern.js', 'js/terms.js']) {
    fs.writeFileSync(path.join(DIST, f), await minifyJs(fs.readFileSync(path.join(SRC, f), 'utf-8')));
  }

  // 3) HTML：内联脚本混淆 + HTML 压缩
  for (const f of ['index.html', 'result.html', 'Print.html']) {
    fs.writeFileSync(path.join(DIST, f), await processHtml(fs.readFileSync(path.join(SRC, f), 'utf-8')));
  }

  console.log('构建完成 ->', DIST);
}
main().catch(e => { console.error('构建失败:', e); process.exit(1); });
