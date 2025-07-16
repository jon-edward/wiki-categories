// Category parsing functionality

function getUnsignedInt32(buffer, offset) {
  // Category IDs are served in big-endian format
  const view = new DataView(buffer, offset, 4);
  return view.getUint32(false);
}

function getUnsignedInt32Array(buffer, offset, length) {
  const output = new Uint32Array(length / 4);
  for (let i = 0; i < length; i += 4) {
    output[i / 4] = getUnsignedInt32(buffer, offset + i);
  }
  return output;
}

async function showCategory(categoryId) {
  const content = await fetch(`${categoryId}.category`);
  const arrayBuffer = await content.arrayBuffer();

  let offset = 0;
  const categoryNameLength = getUnsignedInt32(arrayBuffer, offset);
  offset += 4;

  const categoryName = new TextDecoder().decode(
    arrayBuffer.slice(offset, offset + categoryNameLength)
  );

  offset += categoryNameLength;

  const predecessorsByteLength = getUnsignedInt32(arrayBuffer, offset);
  offset += 4;

  const predecessors = getUnsignedInt32Array(
    arrayBuffer,
    offset,
    predecessorsByteLength
  );

  offset += predecessorsByteLength;

  const successorsByteLength = getUnsignedInt32(arrayBuffer, offset);
  offset += 4;

  const successors = getUnsignedInt32Array(
    arrayBuffer,
    offset,
    successorsByteLength
  );

  offset += successorsByteLength;

  const articlesByteLength = getUnsignedInt32(arrayBuffer, offset);
  offset += 4;

  const articles = getUnsignedInt32Array(
    arrayBuffer,
    offset,
    articlesByteLength
  );

  offset += articlesByteLength;

  const articleNamesByteLength = getUnsignedInt32(arrayBuffer, offset);
  offset += 4;

  const articleNames = new TextDecoder().decode(
    arrayBuffer.slice(offset, offset + articleNamesByteLength)
  );

  const category = {
    name: categoryName,
    predecessors: predecessors,
    successors: successors,
    articles: articles,
    articleNames: articleNames.split("\0"),
  };

  const jsonEncoded = encodeURIComponent(JSON.stringify(category));
  const uri = `data:application/json;charset=utf-8,${jsonEncoded}`;
  window.location.href = uri;
}
