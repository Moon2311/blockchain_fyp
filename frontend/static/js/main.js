// main.js — shared frontend logic for ChainCustody FYP

// ── Auto-dismiss alerts after 5s ─────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert.alert-success, .alert.alert-info').forEach(el => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert && bsAlert.close();
    }, 5000);
  });
});

// ── Copy hash on click ────────────────────────────────────────────
document.addEventListener('click', e => {
  if (e.target.classList.contains('hash-short')) {
    const full = e.target.getAttribute('title');
    if (full) {
      navigator.clipboard.writeText(full).then(() => {
        const orig = e.target.textContent;
        e.target.textContent = 'Copied!';
        setTimeout(() => { e.target.textContent = orig; }, 1500);
      });
    }
  }
});

// ── Blockchain status indicator (navbar dot) ──────────────────────
function updateBlockchainStatus() {
  fetch('/api/status')
    .then(r => r.json())
    .then(data => {
      const dot = document.getElementById('bc-status-dot');
      if (dot) {
        dot.style.background = data.connected && data.deployed ? '#22c55e' : '#ef4444';
        dot.title = data.connected
          ? (data.deployed ? 'Blockchain: Connected & Deployed' : 'Blockchain: Connected but not deployed')
          : 'Blockchain: Offline';
      }
    })
    .catch(() => {});
}

if (document.getElementById('bc-status-dot')) {
  updateBlockchainStatus();
  setInterval(updateBlockchainStatus, 20000);
}
