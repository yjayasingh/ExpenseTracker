const form = document.getElementById("expense-form");
const expenseList = document.getElementById("expense-list");
const filterMonth = document.getElementById("filter-month");
const filterCategory = document.getElementById("filter-category");
const totalMonth = document.getElementById("total-month");
const expenseCount = document.getElementById("expense-count");
const topCategory = document.getElementById("top-category");
const categoryChart = document.getElementById("category-chart");
const toast = document.getElementById("toast");
const receiptInput = document.getElementById("receipt");
const receiptPreview = document.getElementById("receipt-preview");
const receiptModal = document.getElementById("receipt-modal");
const modalImage = document.getElementById("modal-image");

let previewObjectUrl = null;

document.getElementById("expense_date").valueAsDate = new Date();

receiptInput.addEventListener("change", () => {
  if (previewObjectUrl) {
    URL.revokeObjectURL(previewObjectUrl);
    previewObjectUrl = null;
  }
  const file = receiptInput.files[0];
  if (!file) {
    receiptPreview.classList.add("hidden");
    receiptPreview.innerHTML = "";
    return;
  }
  previewObjectUrl = URL.createObjectURL(file);
  receiptPreview.innerHTML = `<img src="${previewObjectUrl}" alt="Receipt preview">`;
  receiptPreview.classList.remove("hidden");
});

receiptModal.querySelectorAll("[data-close-modal]").forEach((el) => {
  el.addEventListener("click", closeReceiptModal);
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeReceiptModal();
});

function openReceiptModal(url) {
  modalImage.src = url;
  receiptModal.classList.remove("hidden");
}

function closeReceiptModal() {
  receiptModal.classList.add("hidden");
  modalImage.src = "";
}

function clearReceiptPreview() {
  if (previewObjectUrl) {
    URL.revokeObjectURL(previewObjectUrl);
    previewObjectUrl = null;
  }
  receiptPreview.classList.add("hidden");
  receiptPreview.innerHTML = "";
}

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.className = "toast show" + (isError ? " error" : "");
  setTimeout(() => toast.classList.remove("show"), 3000);
}

function formatMoney(amount) {
  return new Intl.NumberFormat("en-LK", {
    style: "currency",
    currency: "LKR",
  }).format(amount);
}

function formatDate(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function loadSummary() {
  const month = filterMonth.value;
  const summary = await fetchJSON(`/api/summary?month=${month}`);

  totalMonth.textContent = formatMoney(summary.total);
  expenseCount.textContent = summary.count;

  const top = summary.by_category[0];
  topCategory.textContent = top
    ? `${top.category} (${formatMoney(top.total)})`
    : "—";

  renderCategoryChart(summary.by_category, summary.total);
}

function renderCategoryChart(breakdown, total) {
  if (!breakdown.length) {
    categoryChart.innerHTML = '<p class="empty-state">No expenses yet</p>';
    return;
  }

  const max = breakdown[0].total;
  categoryChart.innerHTML = breakdown
    .map(
      (item) => `
    <div class="bar-row">
      <div class="bar-label">
        <span>${item.category}</span>
        <span>${formatMoney(item.total)} (${total ? Math.round((item.total / total) * 100) : 0}%)</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill" style="width: ${max ? (item.total / max) * 100 : 0}%"></div>
      </div>
    </div>
  `
    )
    .join("");
}

async function loadExpenses() {
  const month = filterMonth.value;
  const category = filterCategory.value;
  let url = `/api/expenses?month=${month}`;
  if (category) url += `&category=${encodeURIComponent(category)}`;

  const expenses = await fetchJSON(url);

  if (!expenses.length) {
    expenseList.innerHTML =
      '<tr><td colspan="6" class="empty-state">No expenses for this period</td></tr>';
    return;
  }

  expenseList.innerHTML = expenses
    .map(
      (e) => `
    <tr>
      <td>${formatDate(e.expense_date)}</td>
      <td>${escapeHtml(e.description)}</td>
      <td><span class="category-badge">${escapeHtml(e.category)}</span></td>
      <td class="amount-col">${formatMoney(e.amount)}</td>
      <td>${receiptCell(e.receipt_url)}</td>
      <td>
        <button class="btn btn-danger" data-id="${e.id}" aria-label="Delete">Delete</button>
      </td>
    </tr>
  `
    )
    .join("");

  expenseList.querySelectorAll(".btn-danger").forEach((btn) => {
    btn.addEventListener("click", () => deleteExpense(btn.dataset.id));
  });

  expenseList.querySelectorAll(".receipt-thumb").forEach((img) => {
    img.addEventListener("click", () => openReceiptModal(img.src));
  });
}

function receiptCell(url) {
  if (!url) return '<span class="receipt-none">—</span>';
  const safe = escapeHtml(url);
  return `<img class="receipt-thumb" src="${safe}" alt="Receipt" title="View receipt">`;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

async function deleteExpense(id) {
  if (!confirm("Delete this expense?")) return;
  try {
    await fetchJSON(`/api/expenses/${id}`, { method: "DELETE" });
    showToast("Expense deleted");
    await refresh();
  } catch (err) {
    showToast(err.message, true);
  }
}

async function refresh() {
  await Promise.all([loadSummary(), loadExpenses()]);
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const formData = new FormData();
  formData.append("amount", document.getElementById("amount").value);
  formData.append("description", document.getElementById("description").value.trim());
  formData.append("category", document.getElementById("category").value);
  formData.append("expense_date", document.getElementById("expense_date").value);

  const receiptFile = receiptInput.files[0];
  if (receiptFile) formData.append("receipt", receiptFile);

  const expenseDate = document.getElementById("expense_date").value;

  try {
    const res = await fetch("/api/expenses", { method: "POST", body: formData });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Request failed");

    form.reset();
    clearReceiptPreview();
    document.getElementById("expense_date").valueAsDate = new Date();
    showToast("Expense added");
    filterMonth.value = expenseDate.slice(0, 7);
    await refresh();
  } catch (err) {
    showToast(err.message, true);
  }
});

filterMonth.addEventListener("change", refresh);
filterCategory.addEventListener("change", loadExpenses);

refresh().catch((err) => showToast(err.message, true));
