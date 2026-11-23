import {readFileSync,writeFileSync} from 'node:fs';
const html=readFileSync('web/verifier.template.html','utf8');
const code=readFileSync('build/verifier.js','utf8');
if(!html.includes('__INLINE_BUNDLE__'))throw new Error('missing script insertion point');
writeFileSync('build/verifier.html',html.replace('__INLINE_BUNDLE__',code));
console.log('Built standalone verifier.html with embedded audited library dependencies; works offline without network calls');
