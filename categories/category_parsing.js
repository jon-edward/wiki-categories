function getUint32(data, offset) {
  const view = new DataView(data, offset, 4);
  return view.getUint32(0, false);
}

function getUint32Array(data, offset, length) {
  const output = new Uint32Array(length / 4);
  for (let i = 0; i < length; i += 4) {
    output[i / 4] = getUint32(data, offset + i);
  }
  return output;
}

function parseCategory(data) {
  let offset = 0;

  function readUint32Array() {
    const len = getUint32(data, offset); // number of elements
    offset += 4;
    const output = getUint32Array(data, offset, len); // pass bytes
    offset += len;
    return output;
  }

  function readString() {
    const len = getUint32(data, offset);
    offset += 4;
    const output = new TextDecoder().decode(data.slice(offset, offset + len));
    offset += len;
    return output;
  }

  const name = readString();
  const predecessors = readUint32Array();
  const successors = readUint32Array();
  const articles = readUint32Array();
  const articleNamesUnsplit = readString();
  const articleNames =
    articleNamesUnsplit.length === 0
      ? []
      : articleNamesUnsplit.split(String.fromCharCode(0));

  return {
    name,
    predecessors,
    successors,
    articles,
    articleNames,
  };
}

function listChild(name, contents) {
  const root = document.createElement("div");
  const title = document.createElement("h3");

  title.textContent = name;
  root.appendChild(title);

  const list = document.createElement("ol");

  for (const child of contents) {
    const listItem = document.createElement("li");
    listItem.textContent = child;
    list.appendChild(listItem);
  }

  if (list.children.length === 0) {
    const listItem = document.createElement("li");
    listItem.textContent = "[None]";
    list.appendChild(listItem);
    list.classList.add("empty");
  }

  root.appendChild(list);
  return root;
}

function pageFromCategory(category) {
  const doc = document.implementation.createHTMLDocument(`${category.name}`);
  const element = doc.body;

  let style = "";

  for (const styleSheet of document.getElementsByTagName("style")) {
    style += styleSheet.innerHTML + "\n";
  }

  const styleElement = doc.createElement("style");
  styleElement.textContent = style;
  element.appendChild(styleElement);

  const name = doc.createElement("h1");
  name.textContent = category.name;
  element.appendChild(name);

  const id = doc.createElement("h3");
  id.textContent = `Id: ${category.id}`;
  element.appendChild(id);

  element.appendChild(listChild("Predecessors", category.predecessors));
  element.appendChild(listChild("Successors", category.successors));
  element.appendChild(listChild("Articles", category.articles));
  element.appendChild(listChild("Article names", category.articleNames));

  return element;
}

async function showCategory(categoryId) {
  const content = await fetch(`${categoryId}.category`);
  const arrayBuffer = await content.arrayBuffer();

  const page = pageFromCategory({
    id: categoryId,
    ...parseCategory(arrayBuffer),
  });

  const blob = new Blob([new XMLSerializer().serializeToString(page)], {
    type: "text/html;charset=utf-8",
  });

  return blob;
}

function clickedCategory(categoryId) {
  const windowReference = window.open("", "_self");
  showCategory(categoryId)
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      windowReference.location.href = url;
    })
    .catch(console.error);
}
