import katex from "katex";
import "katex/contrib/mhchem";


const MATH_SOURCE = String.raw`(?<!\\)\$\$([\s\S]*?)(?<!\\)\$\$|(?<!\\)\$(?!\$)((?:\\.|[^$\n])+?)(?<!\\)\$`;


function mathNode(value, displayMode) {
  const source = value.trim();
  return {
    type: "inlineMath",
    value: source,
    html: katex.renderToString(source, {
      displayMode,
      output: "htmlAndMathml",
      strict: "error",
      throwOnError: true,
      trust: false,
    }),
  };
}


function splitText(node) {
  const matcher = new RegExp(MATH_SOURCE, "g");
  const children = [];
  let cursor = 0;
  for (const match of node.value.matchAll(matcher)) {
    if (match.index > cursor) {
      children.push({ type: "text", value: node.value.slice(cursor, match.index) });
    }
    const displayMode = match[1] != null;
    children.push(mathNode(displayMode ? match[1] : match[2], displayMode));
    cursor = match.index + match[0].length;
  }
  if (cursor === 0) return [node];
  if (cursor < node.value.length) {
    children.push({ type: "text", value: node.value.slice(cursor) });
  }
  return children;
}


function transformChildren(node, insideTable = false) {
  if (!Array.isArray(node.children)) return;
  const inTable = insideTable || node.type === "table";
  node.children = node.children.flatMap((child) => {
    if (inTable && child.type === "text" && typeof child.value === "string") {
      return splitText(child);
    }
    transformChildren(child, inTable);
    return [child];
  });
}


const tableMathTransform = {
  name: "table-math",
  stage: "document",
  plugin: () => (tree) => transformChildren(tree),
};


export default {
  name: "Table math renderer",
  transforms: [tableMathTransform],
};
