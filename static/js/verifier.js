// FeirasWallet — Offline Verifier JS
// Verifies VendorAccessCredential via /verify/check (server resolves DID:KEY offline)

// ── Verification ─────────────────────────────────────────────────────────────

async function runVerification() {
    const input = document.getElementById('credentialInput').value.trim();
    if (!input) { alert('Cole o JSON da credencial ou escaneie o QR code.'); return; }

    let credential;
    try {
        credential = JSON.parse(input);
    } catch (_) {
        showError('JSON inválido. Verifique o conteúdo colado.');
        return;
    }

    showLoading();

    try {
        const res = await fetch('/verify/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ credential })
        });
        const result = await res.json();
        renderResult(result, credential);
    } catch (err) {
        showError('Erro de rede: ' + err.message);
    }
}

async function verifyByClaim(claimId) {
    showLoading();
    try {
        const res = await fetch(`/api/credentials/${claimId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!data.credential) throw new Error('Credencial não encontrada');

        const credInput = document.getElementById('credentialInput');
        if (credInput) credInput.value = JSON.stringify(data.credential, null, 2);

        const verifyRes = await fetch('/verify/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ credential: data.credential })
        });
        const result = await verifyRes.json();
        renderResult(result, data.credential);
    } catch (err) {
        showError('Erro ao buscar credencial: ' + err.message);
    }
}

// ── Rendering ────────────────────────────────────────────────────────────────

function showLoading() {
    const resultsEl = document.getElementById('results');
    if (resultsEl) {
        resultsEl.style.display = 'block';
        resultsEl.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">Verificando...</div>';
    }
}

function showError(msg) {
    const resultsEl = document.getElementById('results');
    if (resultsEl) {
        resultsEl.style.display = 'block';
        resultsEl.innerHTML = `
            <div class="status-banner error">
                <h2>⚠️ Erro</h2>
                <p>${msg}</p>
            </div>
        `;
    }
}

function renderResult(result, credential) {
    const resultsEl = document.getElementById('results');
    if (!resultsEl) return;

    resultsEl.style.display = 'block';

    const sub = (credential && credential.credentialSubject) ? credential.credentialSubject : {};
    const event = sub.event || {};
    const products = Array.isArray(sub.products) ? sub.products : [];

    // ── Status banner ────────────────────────────────────────────────────────
    let bannerClass, bannerIcon, bannerTitle, bannerMsg;

    if (!result.signatureValid) {
        bannerClass = 'invalid';
        bannerIcon = '❌';
        bannerTitle = 'ACESSO NEGADO';
        bannerMsg = 'Assinatura inválida. Credencial adulterada ou não reconhecida.';
    } else if (result.expired) {
        bannerClass = 'expired';
        bannerIcon = '⏰';
        bannerTitle = 'AUTORIZAÇÃO EXPIRADA';
        bannerMsg = 'Credencial expirada. Solicite nova autorização.';
    } else if (result.valid) {
        bannerClass = 'valid';
        bannerIcon = '✅';
        bannerTitle = 'ACESSO AUTORIZADO';
        bannerMsg = 'Assinatura Ed25519 válida · Credencial vigente';
    } else {
        bannerClass = 'invalid';
        bannerIcon = '❌';
        bannerTitle = 'ACESSO NEGADO';
        bannerMsg = result.error || 'Verificação falhou.';
    }

    // ── Stall number (big display) ───────────────────────────────────────────
    const stallDisplay = (result.valid && sub.stallNumber)
        ? `<div class="stall-big">🏪 Banca ${sub.stallNumber}</div>`
        : '';

    // ── Products chips ───────────────────────────────────────────────────────
    const productsHtml = products.length
        ? `<div class="products-chips">${products.map(p => `<span class="chip">${p}</span>`).join('')}</div>`
        : '—';

    // ── Expiration display ───────────────────────────────────────────────────
    const expDate = credential ? credential.expirationDate : null;
    const expDisplay = expDate ? formatDatetime(expDate) : '—';

    // ── Issuer (short) ───────────────────────────────────────────────────────
    const issuer = credential ? credential.issuer : '—';
    const issuerShort = issuer && issuer.length > 40 ? issuer.substring(0, 20) + '...' + issuer.slice(-20) : issuer;

    resultsEl.innerHTML = `
        <div class="status-banner ${bannerClass}">
            <h2>${bannerIcon} ${bannerTitle}</h2>
            <p>${bannerMsg}</p>
        </div>

        ${stallDisplay}

        ${result.valid || result.expired ? `
        <div class="detail-card">
            <h3>Agricultor</h3>
            <div class="detail-row">
                <span class="detail-label">Nome</span>
                <span class="detail-value">${sub.farmerName || '—'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Produtos</span>
                <span class="detail-value">${productsHtml}</span>
            </div>
        </div>

        <div class="detail-card">
            <h3>Evento</h3>
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
                <span class="detail-value">${[event.municipality, event.state].filter(Boolean).join(', ') || '—'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Horário</span>
                <span class="detail-value">${[event.openingTime, event.closingTime].filter(Boolean).join('–') || '—'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Válida até</span>
                <span class="detail-value">${expDisplay}</span>
            </div>
        </div>
        ` : ''}

        <div class="detail-card">
            <h3>Verificação Técnica</h3>
            <div class="detail-row">
                <span class="detail-label">Assinatura Ed25519</span>
                <span class="detail-value">${result.signatureValid ? '✅ Válida' : '❌ Inválida'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Expiração</span>
                <span class="detail-value">${result.expired ? '⚠️ Expirada' : (result.signatureValid ? '✅ Vigente' : '—')}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Método DID</span>
                <span class="detail-value">did:key (offline)</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Emissor</span>
                <span class="detail-value" style="font-size:0.8em">${issuerShort || '—'}</span>
            </div>
        </div>
    `;
}

// ── Date helpers ─────────────────────────────────────────────────────────────

function formatDatetime(isoStr) {
    if (!isoStr) return '—';
    try {
        return new Date(isoStr).toLocaleString('pt-BR', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    } catch (_) { return isoStr; }
}

function formatDateOnly(isoStr) {
    if (!isoStr) return '—';
    try {
        const d = new Date(isoStr + (isoStr.length === 10 ? 'T12:00:00' : ''));
        return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    } catch (_) { return isoStr; }
}
