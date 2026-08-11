export function exportCsv(data: Record<string, unknown>[], name = "mitra-results") {
  if (!data.length) return;
  const keys = Object.keys(data[0]);
  const text = [
    keys.join(","),
    ...data.map(row => keys.map(key => JSON.stringify(row[key] ?? "")).join(","))
  ].join("\n");
  
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
  link.download = `${name}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

export function downloadPng(element: HTMLElement | null, name = "mitra-chart") {
  if (!element) return;
  const svg = element.querySelector("svg");
  if (!svg) return;
  
  const source = new XMLSerializer().serializeToString(svg);
  const img = new Image();
  img.onload = () => {
    const canvas = document.createElement("canvas");
    canvas.width = img.width * 2;
    canvas.height = img.height * 2;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.fillStyle = "#0a0e1a"; // Use var(--bg-deep) equivalent
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    }
    const link = document.createElement("a");
    link.download = `${name}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  };
  img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(source)}`;
}
