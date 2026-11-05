# CSS build

The checked-in output.css is a self-contained fallback, **not** a compiled Tailwind artifact.

CI installs Tailwind CSS v4 CLI, runs:
```
npx @tailwindcss/cli -i ors/static/input.css -o ors/static/output.css --minify
```
and tests the real production CSS. GitHub Actions must complete successfully before Tailwind build is marked verified.

Do not compile Node.js assets on the FastAPI Cloud runtime. Generate CSS before deployment and commit or upload the generated output.
