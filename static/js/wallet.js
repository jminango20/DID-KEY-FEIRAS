// FeirasWallet — PWA wallet JS
// Manages VendorAccessCredential storage in localStorage

const WALLET_KEY = 'feiras_wallet_credentials';

// ── Storage helpers ──────────────────────────────────────────────────────────

function loadCredentials() {
    try {
        return JSON.parse(localStorage.getItem(WALLET_KEY) || '[]');
    } catch (_) {
        return [];
    }
}

function saveCredentials(creds) {
    localStorage.setItem(WALLET_KEY, JSON.stringify(creds));
}

function addCredential(credJson) {
    const creds = loadCredentials();
    const id = credJson.id || credJson.credentialSubject?.id || Date.now().toString();
    if (creds.find(c => c.id === id)) return false;  // already exists
    creds.unshift(credJson);
    saveCredentials(creds);
    return true;
}

function deleteCredential(id) {
    const creds = loadCredentials().filter(c => c.id !== id);
    saveCredentials(creds);
}

// ── Validity helpers ─────────────────────────────────────────────────────────

function isExpired(credential) {
    const exp = credential.expirationDate;
    if (!exp) return false;
    return new Date() > new Date(exp);
}

function formatDate(isoStr) {
    if (!isoStr) return '—';
    try {
        return new Date(isoStr).toLocaleString('pt-BR', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    } catch (_) {
        return isoStr;
    }
}

function formatDateOnly(isoStr) {
    if (!isoStr) return '—';
    try {
        // Handle "2024-06-07" or ISO datetime
        const d = new Date(isoStr + (isoStr.length === 10 ? 'T12:00:00' : ''));
        return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    } catch (_) {
        return isoStr;
    }
}

// ── Wallet Home Page ─────────────────────────────────────────────────────────

function renderWalletHome() {
    const creds = loadCredentials();
    const listEl = document.getElementById('credential-list');
    const emptyEl = document.getElementById('empty-state');

    if (!creds.length) {
        if (emptyEl) emptyEl.style.display = 'block';
        if (listEl) listEl.style.display = 'none';
        return;
    }

    if (emptyEl) emptyEl.style.display = 'none';
    if (listEl) {
        listEl.style.display = 'block';
        listEl.innerHTML = creds.map(cred => buildCredentialCard(cred)).join('');
    }
}

function buildCredentialCard(cred) {
    const sub = cred.credentialSubject || {};
    const event = sub.event || {};
    const expired = isExpired(cred);
    const products = Array.isArray(sub.products) ? sub.products : [];

    return `
        <div class="credential-card">
            <div class="credential-header">
                <div class="credential-icon">🌾</div>
                <div>
                    <h3>${sub.farmerName || 'Agricultor'}</h3>
                    <div class="credential-meta">
                        ${event.name || 'Feira'} · Banca ${sub.stallNumber || '—'}
                    </div>
                </div>
            </div>
            <div class="credential-badges">
                <span class="badge ${expired ? 'badge-expired' : 'badge-valid'}">
                    ${expired ? 'Expirada' : 'Válida'}
                </span>
            </div>
            <div class="credential-details">
                <span>📅 ${formatDateOnly(event.date)}</span>
                <span>📍 ${event.municipality || ''}${event.state ? ', ' + event.state : ''}</span>
                ${products.length ? `<span>🛒 ${products.join(', ')}</span>` : ''}
            </div>
            <div class="credential-actions">
                <button class="btn-view" onclick="viewCredential('${cred.id}')">Ver detalhes</button>
                <button class="btn-delete" onclick="confirmDelete('${cred.id}')">Excluir</button>
            </div>
        </div>
    `;
}

function viewCredential(id) {
    window.location.href = `/wallet/view?id=${encodeURIComponent(id)}`;
}

function confirmDelete(id) {
    if (confirm('Remover esta autorização da sua wallet?')) {
        deleteCredential(id);
        renderWalletHome();
    }
}

// ── Claim Page ───────────────────────────────────────────────────────────────

async function loadClaimPage(claimId) {
    const statusEl = document.getElementById('status');
    const contentEl = document.getElementById('credential-content');
    const saveBtn = document.getElementById('save-btn');

    try {
        const res = await fetch(`/api/credentials/${claimId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (!data.credential) throw new Error('Credencial não encontrada');
        const cred = data.credential;
        const sub = cred.credentialSubject || {};
        const event = sub.event || {};
        const expired = isExpired(cred);
        const products = Array.isArray(sub.products) ? sub.products : [];

        if (statusEl) statusEl.style.display = 'none';

        if (contentEl) {
            contentEl.style.display = 'block';
            contentEl.innerHTML = `
                <div class="issuer-badge">
                    🔐 Emitida por ${cred.issuer || '—'}
                </div>
                <div class="validity-box ${expired ? 'expired' : ''}">
                    ${expired
                        ? '⚠️ Esta autorização já expirou'
                        : `✅ Válida até ${formatDate(cred.expirationDate)}`}
                </div>
                <div class="detail-row">
                    <span class="detail-label">Agricultor</span>
                    <span class="detail-value">${sub.farmerName || '—'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Nº Banca</span>
                    <span class="detail-value">${sub.stallNumber || '—'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Produtos</span>
                    <span class="detail-value">${products.join(', ') || '—'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Feira</span>
                    <span class="detail-value">${event.name || '—'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Data</span>
                    <span class="detail-value">${formatDateOnly(event.date)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Local</span>
                    <span class="detail-value">${event.municipality || ''}${event.state ? ', ' + event.state : ''}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Horário</span>
                    <span class="detail-value">${event.openingTime || ''}–${event.closingTime || ''}</span>
                </div>
            `;
        }

        if (saveBtn) {
            // Check if already in wallet
            const existing = loadCredentials().find(c => c.id === cred.id);
            if (existing) {
                saveBtn.textContent = '✓ Já está na sua wallet';
                saveBtn.disabled = true;
                saveBtn.classList.add('btn-saved');
            } else {
                saveBtn.disabled = false;
                saveBtn.onclick = () => saveToWallet(cred, saveBtn);
            }
        }

        // Mark as claimed server-side (best effort)
        fetch(`/api/credentials/${claimId}/claim`, { method: 'POST' }).catch(() => {});

    } catch (err) {
        if (statusEl) statusEl.textContent = `Erro: ${err.message}`;
        if (saveBtn) saveBtn.disabled = true;
    }
}

function saveToWallet(cred, btn) {
    const added = addCredential(cred);
    if (btn) {
        btn.textContent = added ? '✓ Salvo na wallet!' : '✓ Já estava na wallet';
        btn.disabled = true;
        btn.classList.add('btn-saved');
    }
}

// ── View Credential Page ─────────────────────────────────────────────────────

function loadViewPage() {
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id) { window.location.href = '/wallet/'; return; }

    const cred = loadCredentials().find(c => c.id === decodeURIComponent(id));
    if (!cred) { window.location.href = '/wallet/'; return; }

    const sub = cred.credentialSubject || {};
    const event = sub.event || {};
    const expired = isExpired(cred);
    const products = Array.isArray(sub.products) ? sub.products : [];

    // Validity badge
    const badge = document.getElementById('validity-badge');
    if (badge) {
        badge.className = `validity-badge ${expired ? 'expired' : 'valid'}`;
        badge.textContent = expired ? '⚠️ Autorização Expirada' : '✅ Autorização Válida';
    }

    // Credential subject fields
    setText('v-name', sub.farmerName);
    setText('v-stall', sub.stallNumber);

    const productsEl = document.getElementById('v-products');
    if (productsEl && products.length) {
        productsEl.innerHTML = products.map(p =>
            `<span class="product-tag">${p}</span>`
        ).join('');
        productsEl.parentElement.querySelector('.detail-value')?.classList.remove('detail-value');
    } else if (productsEl) {
        productsEl.innerHTML = products.map(p =>
            `<span class="product-tag">${p}</span>`
        ).join('') || '—';
    }

    // Event fields
    setText('v-event', event.name);
    setText('v-event-date', formatDateOnly(event.date));
    setText('v-location', [event.municipality, event.state].filter(Boolean).join(', '));
    setText('v-time', [event.openingTime, event.closingTime].filter(Boolean).join('–'));
    setText('v-expiration', formatDate(cred.expirationDate));

    // Technical fields
    setText('v-issuer', cred.issuer);
    setText('v-issued', formatDate(cred.issuanceDate));
    setText('v-id', cred.id);

    // JSON
    const jsonEl = document.getElementById('v-json');
    if (jsonEl) jsonEl.textContent = JSON.stringify(cred, null, 2);

    // Copy button
    const copyBtn = document.getElementById('copy-btn');
    if (copyBtn) {
        copyBtn.onclick = () => {
            navigator.clipboard.writeText(JSON.stringify(cred, null, 2))
                .then(() => { copyBtn.textContent = 'Copiado!'; setTimeout(() => { copyBtn.textContent = 'Copiar JSON'; }, 2000); })
                .catch(() => { copyBtn.textContent = 'Erro'; });
        };
    }
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value || '—';
}
