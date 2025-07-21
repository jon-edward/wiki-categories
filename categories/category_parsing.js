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

  return {
    name: readString(),
    successors: readUint32Array(),
    predecessors: readUint32Array(),
    articles: readUint32Array(),
    articleNames: readString().split(String.fromCharCode(0)),
  };
}

async function showCategory(categoryId) {
  const content = await fetch(`${categoryId}.category`);
  const arrayBuffer = await content.arrayBuffer();

  const category = parseCategory(arrayBuffer);

  const jsonEncoded = encodeURIComponent(JSON.stringify(category));
  const uri = `data:application/json;charset=utf-8,${jsonEncoded}`;
  window.location.href = uri;
}
