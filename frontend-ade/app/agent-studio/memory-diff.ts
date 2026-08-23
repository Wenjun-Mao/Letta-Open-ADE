type DiffOp<T> = {
  type: "equal" | "insert" | "delete";
  value: T;
};

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function diffSequence<T>(source: T[], target: T[]): DiffOp<T>[] {
  const sourceLength = source.length;
  const targetLength = target.length;
  const longestCommonSubsequence = Array.from(
    { length: sourceLength + 1 },
    () => Array(targetLength + 1).fill(0),
  );

  for (let sourceIndex = 1; sourceIndex <= sourceLength; sourceIndex += 1) {
    for (let targetIndex = 1; targetIndex <= targetLength; targetIndex += 1) {
      if (source[sourceIndex - 1] === target[targetIndex - 1]) {
        longestCommonSubsequence[sourceIndex][targetIndex] =
          longestCommonSubsequence[sourceIndex - 1][targetIndex - 1] + 1;
      } else {
        longestCommonSubsequence[sourceIndex][targetIndex] = Math.max(
          longestCommonSubsequence[sourceIndex - 1][targetIndex],
          longestCommonSubsequence[sourceIndex][targetIndex - 1],
        );
      }
    }
  }

  const operations: DiffOp<T>[] = [];
  let sourceIndex = sourceLength;
  let targetIndex = targetLength;
  while (sourceIndex > 0 || targetIndex > 0) {
    if (
      sourceIndex > 0
      && targetIndex > 0
      && source[sourceIndex - 1] === target[targetIndex - 1]
    ) {
      operations.push({ type: "equal", value: source[sourceIndex - 1] });
      sourceIndex -= 1;
      targetIndex -= 1;
      continue;
    }

    if (
      targetIndex > 0
      && (
        sourceIndex === 0
        || longestCommonSubsequence[sourceIndex][targetIndex - 1]
          >= longestCommonSubsequence[sourceIndex - 1][targetIndex]
      )
    ) {
      operations.push({ type: "insert", value: target[targetIndex - 1] });
      targetIndex -= 1;
      continue;
    }

    operations.push({ type: "delete", value: source[sourceIndex - 1] });
    sourceIndex -= 1;
  }

  return operations.reverse();
}

function renderInlineDiff(oldLine: string, newLine: string): { oldHtml: string; newHtml: string } {
  const operations = diffSequence([...oldLine], [...newLine]);
  let oldHtml = "";
  let newHtml = "";

  for (const operation of operations) {
    const escaped = escapeHtml(operation.value);
    if (operation.type === "equal") {
      oldHtml += escaped;
      newHtml += escaped;
    } else if (operation.type === "delete") {
      oldHtml += `<span class="diff-removed">${escaped}</span>`;
    } else {
      newHtml += `<span class="diff-added">${escaped}</span>`;
    }
  }

  return { oldHtml, newHtml };
}

export function highlightDiff(oldText: string, newText: string): string {
  const oldValue = oldText || "";
  const newValue = newText || "";
  if (oldValue === newValue) {
    return `<div class="diff-line">${escapeHtml(newValue)}</div>`;
  }

  const lineOperations = diffSequence(oldValue.split("\n"), newValue.split("\n"));
  const chunks: string[] = [];

  for (let index = 0; index < lineOperations.length; index += 1) {
    const current = lineOperations[index];
    if (current.type === "equal") {
      chunks.push(`<div class="diff-line">${escapeHtml(current.value)}</div>`);
      continue;
    }

    const next = lineOperations[index + 1];
    if (current.type === "delete" && next?.type === "insert") {
      const inline = renderInlineDiff(current.value, next.value);
      chunks.push(`<div class="diff-line diff-line-removed"><span class="diff-marker">[-]</span>${inline.oldHtml || " "}</div>`);
      chunks.push(`<div class="diff-line diff-line-added"><span class="diff-marker">[+]</span>${inline.newHtml || " "}</div>`);
      index += 1;
      continue;
    }

    if (current.type === "insert" && next?.type === "delete") {
      const inline = renderInlineDiff(next.value, current.value);
      chunks.push(`<div class="diff-line diff-line-removed"><span class="diff-marker">[-]</span>${inline.oldHtml || " "}</div>`);
      chunks.push(`<div class="diff-line diff-line-added"><span class="diff-marker">[+]</span>${inline.newHtml || " "}</div>`);
      index += 1;
      continue;
    }

    const cssClass = current.type === "delete" ? "diff-removed" : "diff-added";
    const lineClass = current.type === "delete" ? "diff-line-removed" : "diff-line-added";
    const marker = current.type === "delete" ? "[-]" : "[+]";
    chunks.push(
      `<div class="diff-line ${lineClass}"><span class="diff-marker">${marker}</span><span class="${cssClass}">${escapeHtml(current.value)}</span></div>`,
    );
  }

  return chunks.join("");
}
