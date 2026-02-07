document.querySelectorAll("[data-toggle-password]").forEach((button) => {
  button.addEventListener("click", () => {
    const field = button.closest(".password-field");
    if (!field) {
      return;
    }
    const input = field.querySelector("input");
    if (!input) {
      return;
    }

    const isHidden = input.type === "password";
    input.type = isHidden ? "text" : "password";
    button.textContent = isHidden ? "Tutup" : "Lihat";
    button.setAttribute(
      "aria-label",
      isHidden ? "Sembunyikan password" : "Tampilkan password"
    );
  });
});

// Modal Logic for Cetak Bukti
document.addEventListener('DOMContentLoaded', () => {
  const cetakBuktiModal = document.getElementById('cetakBuktiModal');
  const closeButton = cetakBuktiModal ? cetakBuktiModal.querySelector('.close-button') : null;
  const downloadPdfBtn = document.getElementById('downloadPdfBtn');
  const billProofPreview = document.getElementById('billProofPreview');
  let currentBillId = null;
  const adminModal = document.getElementById('adminModal');
  const openAdminModal = document.getElementById('openAdminModal');
  const closeAdminModal = document.getElementById('closeAdminModal');
  const adminEditModal = document.getElementById('adminEditModal');
  const closeAdminEditModal = document.getElementById('closeAdminEditModal');
  const adminEditForm = document.getElementById('adminEditForm');
  const notifBadge = document.getElementById('notifBadge');
  const latestNotifId = notifBadge ? parseInt(notifBadge.getAttribute('data-latest-id') || '0', 10) : 0;

  function formatRupiah(amount) {
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      minimumFractionDigits: 0
    }).format(amount);
  }

  function renderBillProofPreview(billData) {
    if (!billProofPreview) return;

    let htmlContent = `
      <h2 style="text-align: center; margin-bottom: 20px;">BUKTI PEMBAYARAN TAGIHAN LISTRIK</h2>
      <div style="border: 1px solid #eee; padding: 15px; border-radius: 8px; background-color: #f9f9f9;">
        <h3 style="margin-top: 0;">Detail Pelanggan:</h3>
        <p><strong>Nama Pelanggan:</strong> ${billData.nama_pelanggan}</p>
        <p><strong>Nomor KWH:</strong> ${billData.nomor_kwh}</p>
        <p><strong>Alamat:</strong> ${billData.alamat}</p>
      </div>
      <div style="border: 1px solid #eee; padding: 15px; border-radius: 8px; background-color: #f9f9f9; margin-top: 15px;">
        <h3>Detail Tagihan:</h3>
        <p><strong>ID Tagihan:</strong> ${billData.id_tagihan}</p>
        <p><strong>Periode:</strong> ${billData.bulan}/${billData.tahun}</p>
        <p><strong>Jumlah Meter:</strong> ${billData.jumlah_meter} KWH</p>
        <p><strong>Total Bayar:</strong> ${formatRupiah(billData.total_bayar)}</p>
        <p><strong>Status:</strong> <span style="color: green; font-weight: bold;">${billData.status}</span></p>
      </div>
      <p style="text-align: center; margin-top: 20px; font-style: italic;">Terima kasih atas pembayaran Anda.</p>
      <p style="text-align: center; font-size: 0.8em; color: #777;">Dicetak pada: ${new Date().toLocaleString('id-ID')}</p>
    `;
    billProofPreview.innerHTML = htmlContent;
  }

  document.querySelectorAll('.btn-cetak-bukti').forEach(button => {
    button.addEventListener('click', async (event) => {
      currentBillId = event.target.dataset.id_tagihan;
      if (cetakBuktiModal) {
        if (billProofPreview) {
          billProofPreview.innerHTML = '<p style="text-align: center;">Memuat bukti pembayaran...</p>';
        }
        cetakBuktiModal.style.display = 'flex';

        try {
          const response = await fetch(`/api/bill-details/${currentBillId}`);
          if (!response.ok) {
            throw new Error('Gagal mengambil detail tagihan.');
          }
          const billData = await response.json();
          renderBillProofPreview(billData);
        } catch (error) {
          if (billProofPreview) {
            billProofPreview.innerHTML = `<p style="color: red; text-align: center;">Error: ${error.message}</p>`;
          }
          console.error('Error fetching bill details:', error);
        }
      }
    });
  });

  if (closeButton) {
    closeButton.addEventListener('click', () => {
      cetakBuktiModal.style.display = 'none';
    });
  }

  if (cetakBuktiModal) {
    window.addEventListener('click', (event) => {
      if (event.target === cetakBuktiModal) {
        cetakBuktiModal.style.display = 'none';
      }
    });
  }

  if (downloadPdfBtn) {
    downloadPdfBtn.addEventListener('click', async () => {
      if (!currentBillId) {
        alert('ID Tagihan tidak ditemukan.');
        return;
      }

      try {
        const response = await fetch(`/download-bill-proof/${currentBillId}`);
        if (!response.ok) {
          throw new Error('Gagal mengunduh bukti pembayaran.');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `bukti_pembayaran_tagihan_${currentBillId}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
        cetakBuktiModal.style.display = 'none'; // Close modal after download
      } catch (error) {
        alert(error.message);
        console.error('Download error:', error);
      }
    });
  }

  if (openAdminModal && adminModal) {
    openAdminModal.addEventListener('click', () => {
      adminModal.style.display = 'flex';
    });
  }

  if (closeAdminModal && adminModal) {
    closeAdminModal.addEventListener('click', () => {
      adminModal.style.display = 'none';
    });
  }

  if (adminModal) {
    window.addEventListener('click', (event) => {
      if (event.target === adminModal) {
        adminModal.style.display = 'none';
      }
    });
  }

  document.querySelectorAll('[data-edit-admin]').forEach((button) => {
    button.addEventListener('click', () => {
      if (!adminEditModal || !adminEditForm) {
        return;
      }
      const adminId = button.getAttribute('data-id');
      const username = button.getAttribute('data-username') || '';
      const name = button.getAttribute('data-name') || '';
      const level = button.getAttribute('data-level') || '1';

      adminEditForm.action = `/admin/admins/${adminId}/edit`;
      adminEditForm.querySelector('input[name="username"]').value = username;
      adminEditForm.querySelector('input[name="nama_admin"]').value = name;
      adminEditForm.querySelector('input[name="id_level"]').value = level;
      adminEditForm.querySelector('input[name="password"]').value = '';

      adminEditModal.style.display = 'flex';
    });
  });

  if (closeAdminEditModal && adminEditModal) {
    closeAdminEditModal.addEventListener('click', () => {
      adminEditModal.style.display = 'none';
    });
  }

  if (adminEditModal) {
    window.addEventListener('click', (event) => {
      if (event.target === adminEditModal) {
        adminEditModal.style.display = 'none';
      }
    });
  }

  if (notifBadge && latestNotifId) {
    const seenId = parseInt(localStorage.getItem('adminNotifSeenId') || '0', 10);
    if (seenId >= latestNotifId) {
      notifBadge.style.display = 'none';
    }
  }

  document.querySelectorAll('.notif-item').forEach((item) => {
    item.addEventListener('click', () => {
      if (notifBadge && latestNotifId) {
        localStorage.setItem('adminNotifSeenId', String(latestNotifId));
        notifBadge.style.display = 'none';
      }
    });
  });

  const notifItems = Array.from(document.querySelectorAll('.notif-item'));
  const notifMore = document.getElementById('notifMore');
  const notifLess = document.getElementById('notifLess');
  const batchSize = 5;
  let shownCount = batchSize;

  function updateNotifVisibility() {
    notifItems.forEach((item, idx) => {
      item.style.display = idx < shownCount ? 'grid' : 'none';
    });
    if (notifMore) {
      notifMore.style.display = shownCount < notifItems.length ? 'inline-flex' : 'none';
    }
    if (notifLess) {
      notifLess.style.display = shownCount > batchSize ? 'inline-flex' : 'none';
    }
  }

  if (notifItems.length) {
    updateNotifVisibility();
  }

  if (notifMore) {
    notifMore.addEventListener('click', () => {
      shownCount = Math.min(shownCount + batchSize, notifItems.length);
      updateNotifVisibility();
    });
  }

  if (notifLess) {
    notifLess.addEventListener('click', () => {
      shownCount = batchSize;
      updateNotifVisibility();
    });
  }
});
