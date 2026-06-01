const dashboardCategory = document.getElementById("dashboard-category");
const dashboardYear = document.getElementById("dashboard-year");
const dashboardMonth = document.getElementById("dashboard-month");
const dashboardTotal = document.getElementById("dashboard-total");
const dashboardCount = document.getElementById("dashboard-count");
const dashboardChart = document.getElementById("dashboard-chart");
const toast = document.getElementById("toast");

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

async function fetchJSON(url) {
  const res = await fetch(url);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function loadDashboard() {
  const params = new URLSearchParams({
    year: dashboardYear.value,
  });

  if (dashboardMonth.value) params.set("month", dashboardMonth.value);
  if (dashboardCategory.value) params.set("category", dashboardCategory.value);

  const data = await fetchJSON(`/api/dashboard?${params.toString()}`);
  dashboardTotal.textContent = formatMoney(data.total);
  dashboardCount.textContent = data.count;
  renderDashboardChart(data.chart);
}

function renderDashboardChart(points) {
  const hasSpend = points.some((point) => point.total > 0);
  if (!points.length || !hasSpend) {
    dashboardChart.innerHTML = '<p class="empty-state">No expenses for these filters</p>';
    return;
  }

  const max = Math.max(...points.map((point) => point.total));
  dashboardChart.innerHTML = points
    .map((point) => {
      const height = max ? Math.max((point.total / max) * 100, 4) : 0;
      return `
        <div class="dashboard-bar-item">
          <div class="dashboard-bar-value">${formatMoney(point.total)}</div>
          <div class="dashboard-bar-track">
            <div class="dashboard-bar-fill" style="height: ${height}%"></div>
          </div>
          <div class="dashboard-bar-label">${escapeHtml(point.label)}</div>
        </div>
      `;
    })
    .join("");
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

[dashboardCategory, dashboardYear, dashboardMonth].forEach((control) => {
  control.addEventListener("change", () => {
    loadDashboard().catch((err) => showToast(err.message, true));
  });
});

loadDashboard().catch((err) => showToast(err.message, true));
