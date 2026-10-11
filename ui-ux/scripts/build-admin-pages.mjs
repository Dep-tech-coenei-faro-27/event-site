import fs from "node:fs";
import path from "node:path";
import prettier from "prettier";

const root = path.resolve(import.meta.dirname, "..");
const templatePath = path.join(root, "admin", "index.html");
const template = fs.readFileSync(templatePath, "utf8");

const pages = {
  utilizadores: "Utilizadores",
  bilhetes: "Bilhetes",
  transacoes: "Transações",
  apoio: "Apoio",
  paginas: "Páginas e menus",
  programa: "Programa",
  "equipa-parcerias": "Equipa e parcerias",
  comunicacao: "Comunicação",
  "estado-erros": "Estado e erros",
  auditoria: "Auditoria",
  definicoes: "Definições",
};

for (const [view, title] of Object.entries(pages)) {
  const directory = path.join(root, "admin", view);
  const output = template
    .replace(
      "<title>Administração · ENEI 2027</title>",
      `<title>${title} · Administração · ENEI 2027</title>`,
    )
    .replace('data-root=".."', 'data-root="../.."')
    .replace('data-admin-view="overview"', `data-admin-view="${view}"`)
    .replaceAll('href="../styles.css', 'href="../../styles.css')
    .replaceAll('src="../src/', 'src="../../src/')
    .replaceAll('src="../assets/', 'src="../../assets/')
    .replaceAll('href="../"', 'href="../../"')
    .replaceAll('href="./', 'href="../')
    .replace(
      'data-admin-link="overview" aria-current="page"',
      'data-admin-link="overview"',
    )
    .replace(
      `data-admin-link="${view}"`,
      `data-admin-link="${view}" aria-current="page"`,
    );

  fs.mkdirSync(directory, { recursive: true });
  const formatted = await prettier.format(output, { parser: "html" });
  fs.writeFileSync(path.join(directory, "index.html"), formatted, "utf8");
}

console.log(
  `Admin pages: generated ${Object.keys(pages).length} category routes.`,
);
