let displayedProducts = [...products];
let currentFilter = 'all';
let cart = [];
let currentProduct = null;
let currentQty = 1;

const categoryGrid = document.getElementById('categoryGrid');
const productsGrid = document.getElementById('productsGrid');
const searchInput = document.getElementById('searchInput');
const sortSelect = document.getElementById('sortSelect');
const reviewsGrid = document.getElementById('reviewsGrid');
const reviewProduct = document.getElementById('reviewProduct');

function makeStars(value) {
  const rounded = Math.round(value);
  let out = '';
  for (let i = 1; i <= 5; i++) out += i <= rounded ? '★' : '☆';
  return `${out} <span class="muted">(${value})</span>`;
}

function renderCategories() {
  categoryGrid.innerHTML = categories.map(cat => `
    <article class="category-card" data-category="${cat.label}">
      <img src="${cat.image}" alt="${cat.label}">
      <div class="category-content">
        <span class="count-pill">${cat.count}</span>
        <h3>${cat.label}</h3>
        <div class="muted">Browse now →</div>
      </div>
    </article>
  `).join('');

  document.querySelectorAll('.category-card').forEach(card => {
    card.addEventListener('click', () => {
      currentFilter = card.dataset.category;
      document.querySelectorAll('.filters button').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === currentFilter);
      });
      applyFilters();
      document.getElementById('products').scrollIntoView({ behavior: 'smooth' });
    });
  });
}

function renderProducts(list) {
  productsGrid.innerHTML = list.map(product => `
    <article class="product-card">
      <div class="product-image">
        <img src="${product.image}" alt="${product.name}">
        <span class="badge ${product.badge === 'new' ? 'new' : ''}">${product.badge === 'new' ? 'NEW' : 'SALE'}</span>
      </div>
      <div class="product-body">
        <div class="product-cat">${product.category}</div>
        <h3 class="product-title">${product.name}</h3>
        <div class="rating">${makeStars(product.rating)}</div>
        <div class="price-row">
          <div class="price">£${product.price.toFixed(2)}</div>
          <div class="old-price">£${product.oldPrice.toFixed(2)}</div>
        </div>
        <div class="card-actions">
          <button class="btn btn-secondary view-btn" data-id="${product.id}">View</button>
          <button class="btn btn-primary add-btn" data-id="${product.id}">Add</button>
        </div>
      </div>
    </article>
  `).join('');

  document.querySelectorAll('.view-btn').forEach(btn => {
    btn.addEventListener('click', () => openProductModal(Number(btn.dataset.id)));
  });

  document.querySelectorAll('.add-btn').forEach(btn => {
    btn.addEventListener('click', () => addToCart(Number(btn.dataset.id), 1));
  });
}

function renderReviews() {
  reviewsGrid.innerHTML = reviews.map(review => `
    <article class="review-card">
      <div class="rating">${'★'.repeat(review.rating)}${'☆'.repeat(5 - review.rating)}</div>
      <h4>${review.name} on ${review.product}</h4>
      <p>${review.text}</p>
    </article>
  `).join('');
}

function populateReviewProducts() {
  reviewProduct.innerHTML = '<option value="">Choose product</option>' + products.map(p => `<option value="${p.name}">${p.name}</option>`).join('');
}

function applyFilters() {
  const term = searchInput.value.trim().toLowerCase();

  displayedProducts = products.filter(product => {
    const matchesFilter = currentFilter === 'all' || product.category === currentFilter;
    const matchesSearch = product.name.toLowerCase().includes(term) || product.category.toLowerCase().includes(term);
    return matchesFilter && matchesSearch;
  });

  const sortValue = sortSelect.value;
  if (sortValue === 'low-high') displayedProducts.sort((a, b) => a.price - b.price);
  if (sortValue === 'high-low') displayedProducts.sort((a, b) => b.price - a.price);
  if (sortValue === 'rating') displayedProducts.sort((a, b) => b.rating - a.rating);

  renderProducts(displayedProducts);
}

document.querySelectorAll('.filters button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    applyFilters();
  });
});

searchInput.addEventListener('input', applyFilters);
sortSelect.addEventListener('change', applyFilters);

const heroImage = document.getElementById('heroImage');
document.querySelectorAll('.stat-card').forEach(card => {
  card.addEventListener('click', () => {
    document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
    card.classList.add('active');
    heroImage.style.opacity = '0.2';
    setTimeout(() => {
      heroImage.src = card.dataset.img;
      heroImage.style.opacity = '1';
    }, 220);
  });
});

const productOverlay = document.getElementById('productOverlay');
const modalImg = document.getElementById('modalImg');
const modalCategory = document.getElementById('modalCategory');
const modalTitle = document.getElementById('modalTitle');
const modalRating = document.getElementById('modalRating');
const modalPrice = document.getElementById('modalPrice');
const modalOldPrice = document.getElementById('modalOldPrice');
const modalDescription = document.getElementById('modalDescription');
const qtyValue = document.getElementById('qtyValue');

function openProductModal(id) {
  currentProduct = products.find(p => p.id === id);
  currentQty = 1;
  qtyValue.textContent = currentQty;
  modalImg.src = currentProduct.image;
  modalCategory.textContent = currentProduct.category;
  modalTitle.textContent = currentProduct.name;
  modalRating.innerHTML = makeStars(currentProduct.rating);
  modalPrice.textContent = '£' + currentProduct.price.toFixed(2);
  modalOldPrice.textContent = '£' + currentProduct.oldPrice.toFixed(2);
  modalDescription.textContent = currentProduct.description;
  productOverlay.classList.add('show');
}

document.getElementById('closeProductModal').addEventListener('click', () => productOverlay.classList.remove('show'));
productOverlay.addEventListener('click', (e) => {
  if (e.target === productOverlay) productOverlay.classList.remove('show');
});

document.getElementById('qtyMinus').addEventListener('click', () => {
  if (currentQty > 1) currentQty--;
  qtyValue.textContent = currentQty;
});

document.getElementById('qtyPlus').addEventListener('click', () => {
  currentQty++;
  qtyValue.textContent = currentQty;
});

document.getElementById('addToCartFromModal').addEventListener('click', () => {
  if (!currentProduct) return;
  addToCart(currentProduct.id, currentQty);
  productOverlay.classList.remove('show');
});

function addToCart(id, qty) {
  const product = products.find(p => p.id === id);
  const existing = cart.find(item => item.id === id);

  if (existing) {
    existing.qty += qty;
  } else {
    cart.push({ ...product, qty });
  }

  renderCart();
}

const cartPanel = document.getElementById('cartPanel');
document.getElementById('cartBtn').addEventListener('click', () => cartPanel.classList.add('show'));
document.getElementById('closeCart').addEventListener('click', () => cartPanel.classList.remove('show'));

function renderCart() {
  const cartItems = document.getElementById('cartItems');
  const cartCount = document.getElementById('cartCount');
  const cartTotal = document.getElementById('cartTotal');
  const count = cart.reduce((sum, item) => sum + item.qty, 0);
  cartCount.textContent = count;

  if (cart.length === 0) {
    cartItems.innerHTML = '<div class="empty">Your cart is empty.</div>';
    cartTotal.textContent = '£0.00';
    return;
  }

  cartItems.innerHTML = cart.map(item => `
    <div class="cart-item">
      <img src="${item.image}" alt="${item.name}">
      <div>
        <strong>${item.name}</strong>
        <div class="muted">Qty: ${item.qty}</div>
        <div class="muted">£${item.price.toFixed(2)} each</div>
      </div>
      <button class="btn btn-secondary remove-cart-item" data-id="${item.id}">Remove</button>
    </div>
  `).join('');

  cartTotal.textContent = '£' + cart.reduce((sum, item) => sum + item.price * item.qty, 0).toFixed(2);

  document.querySelectorAll('.remove-cart-item').forEach(btn => {
    btn.addEventListener('click', () => {
      cart = cart.filter(item => item.id !== Number(btn.dataset.id));
      renderCart();
    });
  });
}

document.getElementById('purchaseBtn').addEventListener('click', () => {
  if (cart.length === 0) {
    alert('Cart is empty. Add a product first.');
    return;
  }

  alert('Purchase simulated. In a full system this is where checkout would happen after login.');
  cart = [];
  renderCart();
  cartPanel.classList.remove('show');
});

const reviewOverlay = document.getElementById('reviewOverlay');

function openReviewModal(productName = '') {
  reviewOverlay.classList.add('show');
  if (productName) reviewProduct.value = productName;
}

document.getElementById('openReviewBtn').addEventListener('click', () => openReviewModal());
document.getElementById('openReviewBtn2').addEventListener('click', () => openReviewModal());
document.getElementById('openReviewFromModal').addEventListener('click', () => {
  if (currentProduct) openReviewModal(currentProduct.name);
  productOverlay.classList.remove('show');
});
document.getElementById('closeReviewModal').addEventListener('click', () => reviewOverlay.classList.remove('show'));
reviewOverlay.addEventListener('click', (e) => {
  if (e.target === reviewOverlay) reviewOverlay.classList.remove('show');
});

document.querySelectorAll('.format-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const area = document.getElementById('reviewText');
    const tag = btn.dataset.wrap;
    const start = area.selectionStart;
    const end = area.selectionEnd;
    const selected = area.value.slice(start, end) || 'text';
    const wrapped = `<${tag}>${selected}</${tag}>`;
    area.setRangeText(wrapped, start, end, 'end');
    area.focus();
  });
});

document.getElementById('bulletBtn').addEventListener('click', () => {
  const area = document.getElementById('reviewText');
  area.value += '\\n- First point\\n- Second point';
  area.focus();
});

document.getElementById('reviewForm').addEventListener('submit', (e) => {
  e.preventDefault();

  const name = document.getElementById('reviewName').value.trim();
  const product = document.getElementById('reviewProduct').value;
  const rating = Number(document.getElementById('reviewRating').value);
  const text = document.getElementById('reviewText').value.trim();

  if (!name || !product || !rating || !text) return;

  reviews.unshift({ name, product, rating, text });
  renderReviews();
  e.target.reset();
  reviewOverlay.classList.remove('show');
  alert('Review submitted. In a full secure system this would be limited to users who bought the product.');
});

renderCategories();
renderProducts(products);
renderReviews();
populateReviewProducts();
renderCart();
