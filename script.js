document.addEventListener('DOMContentLoaded', () => {
    let cart = JSON.parse(localStorage.getItem('cart')) || [];
    let wishlist = JSON.parse(localStorage.getItem('wishlist')) || [];

    if (cart.length > 0 && typeof cart[0] === 'number') {
        cart = cart.map(id => ({ id: id, quantity: 1, selected: true }));
        localStorage.setItem('cart', JSON.stringify(cart));
    }

    const updateCounters = () => {
        const cartCounters = document.querySelectorAll('.cart-count');
        const wishlistCounters = document.querySelectorAll('.wishlist-count');
        const totalCartItems = cart.reduce((sum, item) => sum + item.quantity, 0);
        cartCounters.forEach(el => el.textContent = totalCartItems);
        wishlistCounters.forEach(el => el.textContent = wishlist.length);
    };

    const saveData = () => {
        localStorage.setItem('cart', JSON.stringify(cart));
        localStorage.setItem('wishlist', JSON.stringify(wishlist));
    };

    const showNotification = (message) => {
        const container = document.getElementById('notification-container');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = `<span class="toast-message">${message}</span><button class="toast-close">&times;</button>`;
        container.appendChild(toast);
        setTimeout(() => toast.classList.add('show'), 100);
        const removeToast = () => {
            toast.classList.remove('show');
            toast.addEventListener('transitionend', () => toast.remove(), { once: true });
        };
        const autoRemoveTimeout = setTimeout(removeToast, 3000);
        toast.querySelector('.toast-close').addEventListener('click', () => {
            clearTimeout(autoRemoveTimeout);
            removeToast();
        });
    };

    const handleProductActions = (container) => {
        container.querySelectorAll('.add-to-cart-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const productId = parseInt(e.currentTarget.dataset.id);
                const existingItem = cart.find(item => item.id === productId);
                if (existingItem) {
                    existingItem.quantity++;
                } else {
                    cart.push({ id: productId, quantity: 1, selected: true });
                }
                saveData();
                updateCounters();
                showNotification('Товар добавлен в корзину');
            });
        });
        container.querySelectorAll('.wishlist-btn').forEach(button => {
            if (wishlist.includes(parseInt(button.dataset.id))) {
                button.classList.add('active');
            }
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const id = parseInt(e.currentTarget.dataset.id);
                if (wishlist.includes(id)) {
                    wishlist = wishlist.filter(itemId => itemId !== id);
                    e.currentTarget.classList.remove('active');
                    showNotification('Удалено из избранного');
                } else {
                    wishlist.push(id);
                    e.currentTarget.classList.add('active');
                    showNotification('Добавлено в избранное');
                }
                saveData();
                updateCounters();
                if (document.body.id === 'wishlist-page') renderWishlist();
                if (document.body.id === 'cart-page') renderCart();
            });
        });
    };

    const lazyLoadImages = () => {
        const lazyImages = document.querySelectorAll('img.lazy-image-original');
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.onload = () => img.classList.add('loaded');
                        observer.unobserve(img);
                    }
                });
            }, { rootMargin: "0px 0px 200px 0px" });
            lazyImages.forEach(img => observer.observe(img));
        } else {
            lazyImages.forEach(img => {
                img.src = img.dataset.src;
                img.classList.add('loaded');
            });
        }
    };

    const renderProductGrid = (containerSelector, products) => {
        const container = document.querySelector(containerSelector);
        if (!container) return;
        if (!products || products.length === 0) {
            container.innerHTML = `<div class="empty-state" style="grid-column: 1 / -1;"><p>По вашему запросу ничего не найдено.</p></div>`;
            return;
        }
        container.innerHTML = products.map(product => `
            <div class="product-card">
                <a href="product.html?id=${product.id}" class="product-link">
                    <div class="product-image lazy-image-container">
                        <img src="${product.previewUrl}" class="lazy-image-preview" alt="${product.name}">
                        <img data-src="${product.imageUrl}" class="lazy-image-original" alt="${product.name}">
                        <button class="wishlist-btn ${wishlist.includes(product.id) ? 'active' : ''}" data-id="${product.id}">
                            <svg viewBox="0 0 24 24"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
                        </button>
                    </div>
                </a>
                <div class="product-info">
                    <a href="product.html?id=${product.id}" class="product-link">
                        <h3 class="product-title">${product.name}</h3>
                    </a>
                    <div class="product-actions">
                        <p class="product-price">${product.price.toLocaleString('ru-RU')} ₽</p>
                        <button class="add-to-cart-btn btn" data-id="${product.id}">В корзину</button>
                    </div>
                </div>
            </div>
        `).join('');
        handleProductActions(container);
        lazyLoadImages();
    };
    
    const renderWishlist = () => {
        const container = document.getElementById('wishlist-container');
        if (!container) return;
        const wishlistProducts = productData.filter(p => wishlist.includes(p.id));
        if (wishlistProducts.length === 0) {
            container.innerHTML = `<div class="empty-state"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg><h2>В избранном пока ничего нет</h2><p>Нажмите на сердечко в каталоге, чтобы добавить товар.</p><a href="catalog.html" class="btn" style="margin-top: 1rem;">Перейти в каталог</a></div>`;
            return;
        }
        renderProductGrid('#wishlist-container', wishlistProducts);
    };

    const renderCart = () => {
        const listContainer = document.getElementById('cart-items-list');
        const summaryContainer = document.getElementById('cart-summary');
        const cartLayout = document.querySelector('.cart-layout');
        const cartTitle = document.querySelector('#cart-page .container > h2');

        if (!listContainer || !summaryContainer || !cartLayout || !cartTitle) return;

        if (cart.length === 0) {
            listContainer.innerHTML = `<div class="empty-state"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.14 0-.25-.11-.25-.25l.03-.12.9-1.63h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49c.08-.14.12-.31.12-.48 0-.55-.45-1-1-1H5.21l-.94-2H1zm16 16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z"/></svg><h2>Ваша корзина пуста</h2><p>Самое время добавить что-нибудь нужное.</p><a href="catalog.html" class="btn" style="margin-top: 1rem;">Перейти в каталог</a></div>`;
            summaryContainer.style.display = 'none';
            cartLayout.classList.add('cart-layout--empty');
            cartTitle.classList.add('cart-title--center');
            return;
        }

        cartLayout.classList.remove('cart-layout--empty');
        cartTitle.classList.remove('cart-title--center');
        summaryContainer.style.display = 'block';

        const allSelected = cart.every(item => item.selected);
        listContainer.innerHTML = `
            <div class="cart-header">
                <label><input type="checkbox" id="select-all-cart" ${allSelected ? 'checked' : ''}> Выбрать все</label>
            </div>
            ${cart.map(cartItem => {
                const product = productData.find(p => p.id === cartItem.id);
                if (!product) return '';
                return `
                    <div class="cart-item">
                        <div class="cart-item-select">
                            <input type="checkbox" class="cart-item-checkbox" data-id="${product.id}" ${cartItem.selected ? 'checked' : ''}>
                            <a href="product.html?id=${product.id}"><img src="${product.imageUrl}" alt="${product.name}"></a>
                        </div>
                        <div class="cart-item-info">
                            <a href="product.html?id=${product.id}"><h4>${product.name}</h4></a>
                            <p class="cart-item-price">${product.price.toLocaleString('ru-RU')} ₽</p>
                        </div>
                        <div class="cart-item-controls">
                            <div class="quantity-selector">
                                <button class="quantity-btn" data-id="${product.id}" data-action="decrease">-</button>
                                <span>${cartItem.quantity}</span>
                                <button class="quantity-btn" data-id="${product.id}" data-action="increase">+</button>
                            </div>
                            <div class="cart-item-actions">
                                <button class="wishlist-btn" data-id="${product.id}"><svg viewBox="0 0 24 24"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg></button>
                                <button class="remove-from-cart-btn" data-id="${product.id}"><svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg></button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('')}
        `;
        
        updateSummary();
        
        listContainer.querySelectorAll('.cart-item-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', e => {
                const productId = parseInt(e.target.dataset.id);
                const itemInCart = cart.find(item => item.id === productId);
                if (itemInCart) {
                    itemInCart.selected = e.target.checked;
                    saveData();
                    updateSummary();
                    document.getElementById('select-all-cart').checked = cart.every(item => item.selected);
                }
            });
        });

        document.getElementById('select-all-cart').addEventListener('change', e => {
            cart.forEach(item => item.selected = e.target.checked);
            saveData();
            renderCart();
        });

        handleProductActions(listContainer);
        listContainer.querySelectorAll('.remove-from-cart-btn').forEach(button => {
            button.addEventListener('click', e => {
                const productId = parseInt(e.currentTarget.dataset.id);
                cart = cart.filter(item => item.id !== productId);
                showNotification('Товар удален из корзины');
                saveData(); updateCounters(); renderCart();
            });
        });
        listContainer.querySelectorAll('.quantity-btn').forEach(button => {
            button.addEventListener('click', e => {
                const productId = parseInt(e.currentTarget.dataset.id);
                const action = e.currentTarget.dataset.action;
                const itemInCart = cart.find(item => item.id === productId);
                if (itemInCart) {
                    if (action === 'increase') {
                        itemInCart.quantity++;
                    } else if (action === 'decrease') {
                        if (itemInCart.quantity > 1) {
                            itemInCart.quantity--;
                        } else {
                            cart = cart.filter(item => item.id !== productId);
                            showNotification('Товар удален из корзины');
                        }
                    }
                    saveData(); updateCounters(); renderCart();
                }
            });
        });
    };

    const updateSummary = () => {
        const checkoutBtn = document.getElementById('checkout-btn');
        const subtotalPriceEl = document.getElementById('subtotal-price');
        const courierCostEl = document.getElementById('courier-cost');
        const finalTotalPriceEl = document.getElementById('final-total-price');
        const totalWeightEl = document.getElementById('total-weight');

        if (!checkoutBtn || !subtotalPriceEl || !finalTotalPriceEl || !courierCostEl || !totalWeightEl) return;

        const DELIVERY_COST = 300;
        const FREE_DELIVERY_THRESHOLD = 5000;

        const selectedItems = cart.filter(item => item.selected);
        const totalItems = selectedItems.reduce((sum, item) => sum + item.quantity, 0);
        
        const subtotalPrice = selectedItems.reduce((sum, item) => {
            const product = productData.find(p => p.id === item.id);
            return sum + (product.price * item.quantity);
        }, 0);
        
        const totalWeight = selectedItems.reduce((sum, item) => {
            const product = productData.find(p => p.id === item.id);
            return sum + (parseFloat(product.details['Вес'] || 0) * item.quantity);
        }, 0);

        const selectedDelivery = document.querySelector('input[name="delivery"]:checked').value;
        let deliveryCost = 0;

        if (subtotalPrice >= FREE_DELIVERY_THRESHOLD) {
            courierCostEl.innerHTML = `<s>300 ₽</s> Бесплатно`;
            if(selectedDelivery === 'courier') {
                deliveryCost = 0;
            }
        } else {
            courierCostEl.innerHTML = `300 ₽`;
            if(selectedDelivery === 'courier') {
                deliveryCost = DELIVERY_COST;
            }
        }

        const finalPrice = subtotalPrice + deliveryCost;

        subtotalPriceEl.textContent = `${subtotalPrice.toLocaleString('ru-RU')} ₽`;
        totalWeightEl.textContent = `${(totalWeight / 1000).toFixed(2)} кг`;
        finalTotalPriceEl.textContent = `${finalPrice.toLocaleString('ru-RU')} ₽`;
        checkoutBtn.disabled = selectedItems.length === 0;

        const subtotalRowEl = document.getElementById('subtotal-row');
        subtotalRowEl.querySelector('span').textContent = `Товары (${totalItems} шт.)`;
    };

    const renderProductDetail = () => {
        const container = document.getElementById('product-detail-container');
        if (!container) return;
        const urlParams = new URLSearchParams(window.location.search);
        const productId = parseInt(urlParams.get('id'));
        const product = productData.find(p => p.id === productId);
        if (!product) { container.innerHTML = '<h2>Товар не найден</h2>'; return; }
        document.title = `Охота и Рыбалка - ${product.name}`;
        container.innerHTML = `<div class="product-detail-image"><img src="${product.imageUrl}" alt="${product.name}"></div><div class="product-detail-info"><h1>${product.name}</h1><p class="product-detail-price">${product.price.toLocaleString('ru-RU')} ₽</p><div class="product-detail-actions"><button class="btn add-to-cart-btn" data-id="${product.id}">В корзину</button><button class="wishlist-btn icon-btn ${wishlist.includes(product.id) ? 'active' : ''}" data-id="${product.id}"><svg viewBox="0 0 24 24"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg></button></div><h3>Описание</h3><p>${product.description}</p><h3>Характеристики</h3><div class="details-grid">${Object.entries(product.details).map(([key, value]) => `<div class="detail-item"><span>${key}</span><span>${value}</span></div>`).join('')}</div></div>`;
        handleProductActions(container);
    };
    
    const setupModal = () => {
        const checkoutBtn = document.getElementById('checkout-btn');
        const modal = document.getElementById('checkout-modal');
        if (!checkoutBtn || !modal) return;
        
        const closeBtn = modal.querySelector('.close-btn');
        const orderForm = modal.querySelector('#order-form');
        const paymentRadios = orderForm.querySelectorAll('input[name="payment-method"]');
        const changeGroup = orderForm.querySelector('#change-group');
        const phoneInput = orderForm.querySelector('#customer-phone');
        const modalAddressGroup = document.getElementById('address-group');

        const applyPhoneMask = (e) => {
            const input = e.target;
            let value = input.value.replace(/\D/g, '');
            let formattedValue = '+7 (';
            if (value.length > 1) formattedValue += value.substring(1, 4);
            if (value.length >= 5) formattedValue += ') ' + value.substring(4, 7);
            if (value.length >= 8) formattedValue += '-' + value.substring(7, 9);
            if (value.length >= 10) formattedValue += '-' + value.substring(9, 11);
            input.value = formattedValue;
        };
        if(phoneInput) phoneInput.addEventListener('input', applyPhoneMask);

        if(paymentRadios) {
            paymentRadios.forEach(radio => radio.addEventListener('change', () => {
                if (radio.value === 'cash') {
                    changeGroup.classList.add('visible');
                    changeGroup.classList.remove('hidden');
                } else {
                    changeGroup.classList.remove('visible');
                    changeGroup.classList.add('hidden');
                }
            }));
        }
        
        const validateForm = () => {
            let isValid = true;
            const inputsToValidate = orderForm.querySelectorAll('[required]');
            inputsToValidate.forEach(input => {
                const errorSpan = input.parentElement.querySelector('.error-message');
                input.classList.remove('error');
                if (errorSpan) errorSpan.textContent = '';
                if (input.value.trim() === '') {
                    isValid = false;
                    input.classList.add('error');
                    if (errorSpan) errorSpan.textContent = 'Это поле обязательно для заполнения';
                } else if (input.type === 'tel' && input.value.replace(/\D/g, '').length !== 11) {
                     isValid = false;
                    input.classList.add('error');
                    if (errorSpan) errorSpan.textContent = 'Введите корректный номер телефона';
                }
            });
            const isCourier = document.querySelector('input[name="delivery"]:checked').value === 'courier';
            const addressTextarea = orderForm.querySelector('#customer-address');
            const addressErrorSpan = modalAddressGroup.querySelector('.error-message');
            addressTextarea.classList.remove('error');
            if (addressErrorSpan) addressErrorSpan.textContent = '';
            if (isCourier && addressTextarea.value.trim() === '') {
                isValid = false;
                addressTextarea.classList.add('error');
                if (addressErrorSpan) addressErrorSpan.textContent = 'Введите адрес для доставки';
            }
            return isValid;
        };

        if(orderForm) {
            orderForm.addEventListener('submit', function(e) {
                e.preventDefault();
                if (!validateForm()) { return; }
                var submitButton = orderForm.querySelector('button[type="submit"]');
                submitButton.disabled = true;
                submitButton.textContent = 'Отправка...';
                var subtotalPriceText = document.getElementById('final-total-price').textContent;
                var isCourier = document.querySelector('input[name="delivery"]:checked').value === 'courier';
                var deliveryCostNum = 0;
                if (isCourier) {
                    var subtotalPrice = parseInt(subtotalPriceText.replace(/\s/g, ''));
                    deliveryCostNum = subtotalPrice >= 5000 ? 0 : 300;
                }
                var selectedItems = cart.filter(function(item) { return item.selected; });
                var orderData = {
                    name: document.getElementById('customer-name').value,
                    phone: document.getElementById('customer-phone').value,
                    comment: document.getElementById('customer-comment').value,
                    address: isCourier ? document.getElementById('customer-address').value : 'Самовывоз',
                    paymentMethod: document.querySelector('input[name="payment-method"]:checked').value,
                    cashChange: document.getElementById('cash-change').value,
                    items: selectedItems.map(function(item) {
                        var product = productData.find(function(p) { return p.id === item.id; });
                        return { name: product.name, quantity: item.quantity, price: (product.price * item.quantity).toLocaleString('ru-RU') };
                    }),
                    deliveryCost: deliveryCostNum.toLocaleString('ru-RU'),
                    totalPrice: subtotalPriceText
                };
                fetch('https://klas0.pythonanywhere.com/submit-order', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(orderData)
                })
                .then(function(response) {
                    if (!response.ok) {
                        return response.json().then(function(err) { throw new Error(JSON.stringify(err.message || 'Server error')); });
                    }
                    return response.json();
                })
                .then(function(data) {
                    var modalContent = modal.querySelector('.modal-content');
                    modalContent.innerHTML = '<h2>Спасибо за заказ! (´-ω-`)</h2><p>Наш менеджер скоро свяжется с вами. Страница перезагрузится через несколько секунд...</p>';
                    cart = cart.filter(function(item) { return !item.selected; });
                    saveData();
                    setTimeout(function() { window.location.reload(); }, 4000);
                })
                .catch(function(error) {
                    console.error('Ошибка отправки заказа:', error);
                    submitButton.disabled = false;
                    submitButton.textContent = 'Заказать';
                    alert('Произошла ошибка при отправке заказа. Пожалуйста, попробуйте еще раз.\n\nОшибка: ' + error.message);
                });
            });
        }

        checkoutBtn.addEventListener('click', () => {
            if (cart.filter(item => item.selected).length > 0) {
                const selectedDelivery = document.querySelector('input[name="delivery"]:checked').value;
                const cardLabel = document.getElementById('card-payment-label');
                if (selectedDelivery === 'pickup') {
                    cardLabel.textContent = 'Картой в магазине';
                    modalAddressGroup.classList.remove('visible');
                    modalAddressGroup.classList.add('hidden');
                } else {
                    cardLabel.textContent = 'Картой курьеру';
                    modalAddressGroup.classList.add('visible');
                    modalAddressGroup.classList.remove('hidden');
                }
                modal.style.display = 'flex';
            }
        });

        const closeModal = () => { modal.style.display = 'none'; };
        if(closeBtn) closeBtn.addEventListener('click', closeModal);
        window.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
    };

    const debounce = (func, delay) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    };
    
    const initLiveSearch = () => {
        const searchForms = document.querySelectorAll('.search-form');
        searchForms.forEach(form => {
            const searchInput = form.querySelector('input');
            const resultsContainer = form.querySelector('#search-results');
            if (!searchInput || !resultsContainer) return;
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                const query = searchInput.value.trim();
                if (query) {
                    window.location.href = `catalog.html?search=${encodeURIComponent(query)}`;
                }
            });
            const handleSearch = () => {
                const query = searchInput.value.trim().toLowerCase();
                resultsContainer.innerHTML = '';
                if (query.length < 2) {
                    resultsContainer.classList.remove('active');
                    return;
                }
                const matches = productData.filter(product => product.name.toLowerCase().includes(query));
                resultsContainer.classList.add('active');
                if (matches.length > 0) {
                    resultsContainer.innerHTML = matches.slice(0, 5).map(product => `
                        <a href="product.html?id=${product.id}" class="search-result-item">
                            <div class="search-result-info">
                                <h4>${product.name}</h4>
                                <p>${product.price.toLocaleString('ru-RU')} ₽</p>
                            </div>
                        </a>
                    `).join('');
                    if (matches.length > 5) {
                        resultsContainer.innerHTML += `<a href="catalog.html?search=${encodeURIComponent(query)}" class="search-result-footer">Показать все результаты (${matches.length})</a>`;
                    }
                } else {
                    resultsContainer.innerHTML = `<div class="no-results">Ничего не найдено</div>`;
                }
            };
            searchInput.addEventListener('input', debounce(handleSearch, 300));
            document.addEventListener('click', (e) => {
                if (!form.contains(e.target)) {
                    resultsContainer.classList.remove('active');
                }
            });
        });
    };
    
    // --- ЛОГИКА ЗАПУСКА ДЛЯ КАЖДОЙ СТРАНИЦЫ ---
    if (document.body.id === 'catalog-page') {
        const applyFiltersAndSort = () => {
            let filtered = [...productData];
            const activeCategory = document.querySelector('#category-filter a.active')?.dataset.category;
            if (activeCategory && activeCategory !== 'all') {
                filtered = filtered.filter(p => p.category === activeCategory);
            }
            const minPrice = parseFloat(document.getElementById('min-price').value);
            const maxPrice = parseFloat(document.getElementById('max-price').value);
            if (!isNaN(minPrice)) filtered = filtered.filter(p => p.price >= minPrice);
            if (!isNaN(maxPrice)) filtered = filtered.filter(p => p.price <= maxPrice);
            const searchInput = document.querySelector('#catalog-page .search-bar input');
            if (searchInput && searchInput.value) {
                const searchQuery = searchInput.value.trim().toLowerCase();
                if (searchQuery) {
                    filtered = filtered.filter(p => p.name.toLowerCase().includes(searchQuery));
                }
            }
            const sortBy = document.getElementById('sort-by').value;
            switch(sortBy) {
                case 'price-asc': filtered.sort((a, b) => a.price - b.price); break;
                case 'price-desc': filtered.sort((a, b) => b.price - a.price); break;
                case 'name-asc': filtered.sort((a, b) => a.name.localeCompare(b.name)); break;
            }
            document.getElementById('product-count').textContent = `Найдено: ${filtered.length}`;
            renderProductGrid('.grid', filtered);
        };
        document.querySelectorAll('#category-filter a').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                document.querySelector('#category-filter a.active').classList.remove('active');
                e.target.classList.add('active');
                applyFiltersAndSort();
            });
        });
        document.getElementById('price-filter').addEventListener('submit', (e) => { e.preventDefault(); applyFiltersAndSort(); });
        document.getElementById('price-filter').addEventListener('reset', () => setTimeout(applyFiltersAndSort, 0));
        document.getElementById('sort-by').addEventListener('change', applyFiltersAndSort);
        const catalogSearchInput = document.querySelector('#catalog-page .search-bar input');
        if (catalogSearchInput) {
            catalogSearchInput.addEventListener('input', debounce(applyFiltersAndSort, 300));
        }
        const urlParams = new URLSearchParams(window.location.search);
        const categoryQuery = urlParams.get('category');
        const searchQuery = urlParams.get('search');
        if (categoryQuery) {
            document.querySelector('#category-filter a.active').classList.remove('active');
            const categoryLink = document.querySelector(`#category-filter a[data-category="${categoryQuery}"]`);
            if (categoryLink) categoryLink.classList.add('active');
        }
        if (searchQuery) {
            const searchInput = document.querySelector('.search-bar input');
            if(searchInput) searchInput.value = searchQuery;
        }
        applyFiltersAndSort();
    } else if (document.body.id === 'home-page') {
        // --- ЛОГИКА ДЛЯ ХИТОВ ПРОДАЖ ---
        const hitProductIds = [24, 16, 48, 15, 11, 6, 54, 12];
        const hitProducts = productData.filter(p => hitProductIds.includes(p.id));
        const sortedHitProducts = hitProductIds.map(id => hitProducts.find(p => p.id === id)).filter(p => p);
        renderProductGrid('.hits .grid', sortedHitProducts);
        
        // --- ЛОГИКА ДЛЯ КАРТИНОК КАТЕГОРИЙ ---
        lazyLoadImages();

        // --- ВОЗВРАЩАЕМ ЛОГИКУ ДЛЯ ЛЕНИВОЙ ЗАГРУЗКИ ВИДЕО ---
        const heroSection = document.querySelector('.hero-section');
        if (heroSection) {
            const video = heroSection.querySelector('.hero-video');
            if (video && typeof video.play === 'function') {
                video.addEventListener('canplaythrough', () => {
                    heroSection.classList.add('video-loaded');
                    video.play();
                }, { once: true });
            }
        }
    } else if (document.body.id === 'cart-page') {
        renderCart();
        setupModal();
        document.querySelectorAll('input[name="delivery"]').forEach(radio => {
            radio.addEventListener('change', updateSummary);
        });
    } else if (document.body.id === 'wishlist-page') {
        renderWishlist();
    } else if (document.body.id === 'product-page') {
        renderProductDetail();
    }

    const header = document.querySelector('.header');
    let lastScrollY = window.scrollY;
    
    const handleScroll = () => {
        const currentScrollY = window.scrollY;
        const stickyElements = document.querySelectorAll('.filters, .cart-summary');
        if (currentScrollY > lastScrollY && currentScrollY > 100) {
            header.classList.add('sticky');
        } else if (currentScrollY < lastScrollY) {
            header.classList.remove('sticky');
        }
        const headerBottom = document.querySelector('.header-bottom');
        const headerVisibleHeight = header.classList.contains('sticky') ? (headerBottom?.offsetHeight || 0) : header.offsetHeight;
        stickyElements.forEach(el => {
            el.style.top = `${headerVisibleHeight + 20}px`;
        });
        lastScrollY = currentScrollY <= 0 ? 0 : currentScrollY; 
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    
    const burger = document.querySelector('.burger-menu');
    const nav = document.querySelector('.mobile-nav-panel');
    const overlay = document.querySelector('.overlay');
    const body = document.body;

    if (burger && nav && overlay) {
        const closeMenu = () => {
            nav.classList.remove('active');
            overlay.classList.remove('active');
            body.classList.remove('menu-open');
        };
        burger.addEventListener('click', () => {
            nav.classList.toggle('active');
            overlay.classList.toggle('active');
            body.classList.toggle('menu-open');
        });
        overlay.addEventListener('click', closeMenu);
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1 });
    document.querySelectorAll('.animate-on-scroll').forEach(el => observer.observe(el));

    initLiveSearch();
    updateCounters();

    // --- ФИНАЛЬНАЯ ЛОГИКА ДЛЯ СИСТЕМЫ ОТЗЫВОВ ---
    if (document.body.id === 'reviews-page') {
        const reviewsContainer = document.getElementById('reviews-container');
        const reviewForm = document.getElementById('review-form');
        const sortSelect = document.getElementById('reviews-sort');
        const paginationTop = document.getElementById('pagination-controls-top');
        const paginationBottom = document.getElementById('pagination-controls-bottom');

        const API_BASE_URL = 'https://klas0.pythonanywhere.com';

        const setupCharCounter = (inputId, counterId, maxLength) => {
            const input = document.getElementById(inputId);
            const counter = document.getElementById(counterId);
            if (input && counter) {
                const updateCounter = () => {
                    const remaining = maxLength - input.value.length;
                    counter.textContent = remaining < 0 ? 'Лимит!' : remaining;
                    counter.classList.toggle('error', remaining < 0);
                };
                input.addEventListener('input', updateCounter);
                updateCounter();
            }
        };
        setupCharCounter('review-name', 'name-char-counter', 50);
        setupCharCounter('review-text', 'text-char-counter', 2000);

        let userId = localStorage.getItem('reviewUserId');
        if (!userId) {
            userId = 'user_' + Date.now() + Math.random().toString(36).substring(2, 15);
            localStorage.setItem('reviewUserId', userId);
        }

        let currentPage = 1;

        const createStarRating = (rating) => {
            if (!rating) return '';
            const starSVG = `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M9.15316 5.40838C10.4198 3.13613 11.0531 2 12 2C12.9469 2 13.5802 3.13612 14.8468 5.40837L15.1745 5.99623C15.5345 6.64193 15.7144 6.96479 15.9951 7.17781C16.2757 7.39083 16.6251 7.4699 17.3241 7.62805L17.9605 7.77203C20.4201 8.32856 21.65 8.60682 21.9426 9.54773C22.2352 10.4886 21.3968 11.4691 19.7199 13.4299L19.2861 13.9372C18.8096 14.4944 18.5713 14.773 18.4641 15.1177C18.357 15.4624 18.393 15.8341 18.465 16.5776L18.5306 17.2544C18.7841 19.8706 18.9109 21.1787 18.1449 21.7602C17.3788 22.3417 16.2273 21.8115 13.9243 20.7512L13.3285 20.4768C12.6741 20.1755 12.3469 20.0248 12 20.0248C11.6531 20.0248 11.3259 20.1755 10.6715 20.4768L10.0757 20.7512C7.77268 21.8115 6.62118 22.3417 5.85515 21.7602C5.08912 21.1787 5.21588 19.8706 5.4694 17.2544L5.53498 16.5776C5.60703 15.8341 5.64305 15.4624 5.53586 15.1177C5.42868 14.773 5.19043 14.4944 4.71392 13.9372L4.2801 13.4299C2.60325 11.4691 1.76482 10.4886 2.05742 9.54773C2.35002 8.60682 3.57986 8.32856 6.03954 7.77203L6.67589 7.62805C7.37485 7.4699 7.72433 7.39083 8.00494 7.17781C8.28555 6.96479 8.46553 6.64194 8.82547 5.99623L9.15316 5.40838Z"/></svg>`;
            return `<div class="review-rating">${Array.from({length: 5}, (_, i) => `<span class="star ${i < rating ? '' : 'empty'}">${starSVG}</span>`).join('')}</div>`;
        };

        const createReviewHTML = (review) => {
            const date = new Date(review.timestamp + 'Z');
            const formattedDate = date.toLocaleString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });
            const adminBadgeSVG = `<svg class="admin-badge" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M12,1L3,5V11C3,16.55 6.84,21.74 12,23C17.16,21.74 21,16.55 21,11V5L12,1Z"/></svg>`;
            const score = (review.upvotes || 0) - (review.downvotes || 0);
            const scoreClass = score > 0 ? 'positive' : score < 0 ? 'negative' : '';
            const scoreText = score > 0 ? `+${score}` : (score < 0 ? score : '0');
            const reviewTextHtml = review.text.replace(/\n/g, '<br>');

            return `<div class="review-card" id="review-${review.id}">
                <div class="review-voting">
                    <button class="vote-btn up ${review.user_vote === 1 ? 'voted' : ''}" data-review-id="${review.id}" data-vote-type="1"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7"></path></svg></button>
                    <span class="vote-score ${scoreClass}" id="score-${review.id}">${scoreText}</span>
                    <button class="vote-btn down ${review.user_vote === -1 ? 'voted' : ''}" data-review-id="${review.id}" data-vote-type="-1"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"></path></svg></button>
                </div>
                <div class="review-content">
                    <div class="review-header">${review.is_admin_reply ? `${adminBadgeSVG}<span class="review-author admin">${review.name}</span>` : `<span class="review-author">${review.name}</span>`}</div>
                    ${createStarRating(review.rating)}
                    <p class="review-text">${reviewTextHtml}</p>
                    <div class="review-footer">
                        <span class="review-date">${formattedDate}</span>
                        <button class="reply-btn" data-parent-id="${review.parent_id || review.id}" data-author="${review.name}">Ответить</button>
                        ${review.reply_count > 0 ? `<button class="reply-btn show-replies-btn" data-parent-id="${review.id}">💬 Показать ответы (${review.reply_count})</button>` : ''}
                    </div>
                    <div class="replies-container" id="replies-for-${review.id}"></div>
                    <div class="reply-form-container" id="reply-form-for-${review.id}"></div>
                </div>
            </div>`;
        };
        
        const renderPaginationControls = (totalPages, currentPage) => {
    if (totalPages <= 1) {
        paginationTop.innerHTML = '';
        paginationBottom.innerHTML = '';
        return;
    }

    // SVG иконки для стрелок
    const arrowLeftSVG = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"></path></svg>`;
    const arrowRightSVG = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"></path></svg>`;

    // Генерируем HTML для пагинации
    const buttonsHTML = `
        <button class="pagination-arrow" data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
            ${arrowLeftSVG}
        </button>
        <span class="pagination-info">Стр. ${currentPage} из ${totalPages}</span>
        <button class="pagination-arrow" data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
            ${arrowRightSVG}
        </button>
    `;
    
    paginationTop.innerHTML = buttonsHTML;
    paginationBottom.innerHTML = buttonsHTML;
};


        const fetchAndRenderReviews = async (page = 1) => {
            const sortBy = sortSelect.value;
            reviewsContainer.innerHTML = '<p class="loading-text" style="text-align: center; color: #999;">Загрузка отзывов...</p>';
            paginationTop.innerHTML = ''; 
            paginationBottom.innerHTML = '';
            try {
                const response = await fetch(`${API_BASE_URL}/get-reviews?sort=${sortBy}&user_id=${userId}&page=${page}&limit=10`);
                if (!response.ok) throw new Error('Ошибка загрузки отзывов');
                const data = await response.json();
                const reviews = data.reviews;
                if (!reviews || reviews.length === 0) {
                    reviewsContainer.innerHTML = '<p class="empty-text" style="text-align: center; color: #999;">Отзывов пока нет. Будьте первым!</p>';
                    return;
                }
                reviewsContainer.innerHTML = reviews.map(createReviewHTML).join('');
                currentPage = data.current_page;
                renderPaginationControls(data.total_pages, data.current_page);
            } catch (error) {
                console.error(error);
                reviewsContainer.innerHTML = '<p class="error-text" style="text-align: center; color: var(--accent-red);">Не удалось загрузить отзывы.</p>';
            }
        };

        reviewForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const ratingInput = reviewForm.querySelector('input[name="rating"]:checked');
            const nameInput = document.getElementById('review-name');
            const textInput = document.getElementById('review-text');
            if (!ratingInput) { showNotification('Пожалуйста, поставьте оценку (звездочки)'); return; }
            if (textInput.value.trim() === '') { showNotification('Текст отзыва не может быть пустым'); return; }
            if (nameInput.value.length > 50 || textInput.value.length > 2000) { showNotification('Превышен лимит символов в имени или тексте отзыва.'); return; }

            const submitButton = reviewForm.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            submitButton.textContent = 'Отправка...';
            try {
                const response = await fetch(`${API_BASE_URL}/add-review`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: nameInput.value.trim() || "Аноним",
                        text: textInput.value,
                        rating: parseInt(ratingInput.value)
                    })
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.message || 'Ошибка сервера');
                
                if (result.review) {
                    fetchAndRenderReviews(1); // Перезагружаем отзывы с первой страницы
                    reviewForm.reset();
                    setupCharCounter('review-name', 'name-char-counter', 50);
                    setupCharCounter('review-text', 'text-char-counter', 2000);
                    showNotification('Ваш отзыв опубликован!');
                } else {
                    const thanksModal = document.createElement('div');
                    thanksModal.className = 'modal';
                    thanksModal.style.display = 'flex';
                    thanksModal.innerHTML = `<div class="modal-content"><h2>Спасибо за ваш отзыв! (. ❛ ᴗ ❛.)</h2><p style="margin: 1rem 0; color: #555;">Он появится на сайте после проверки модератором. Страница скоро обновится.</p></div>`;
                    document.body.appendChild(thanksModal);
                    setTimeout(() => { window.location.reload(); }, 4000);
                }
            } catch (error) {
                console.error(error);
                showNotification(`Ошибка: ${error.message}`);
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = 'Отправить отзыв';
            }
        });

        reviewsContainer.addEventListener('click', async (e) => {
            const target = e.target;
            const voteButton = target.closest('.vote-btn');
            
            if (voteButton) {
                const reviewId = voteButton.dataset.reviewId;
                const voteType = parseInt(voteButton.dataset.voteType);
                voteButton.disabled = true;
                try {
                    const response = await fetch(`${API_BASE_URL}/vote`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ review_id: reviewId, user_id: userId, vote_type: voteType })
                    });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.message);
                    
                    const scoreEl = document.getElementById(`score-${reviewId}`);
                    const score = result.upvotes - result.downvotes;
                    const scoreText = score > 0 ? `+${score}` : (score < 0 ? score : '0');
                    scoreEl.textContent = scoreText;
                    scoreEl.className = 'vote-score';
                    if (score > 0) scoreEl.classList.add('positive');
                    if (score < 0) scoreEl.classList.add('negative');

                    const parentCard = voteButton.closest('.review-card');
                    const upBtn = parentCard.querySelector('.vote-btn.up');
                    const downBtn = parentCard.querySelector('.vote-btn.down');
                    const wasVoted = voteButton.classList.contains('voted');
                    upBtn.classList.remove('voted');
                    downBtn.classList.remove('voted');
                    if (!wasVoted) {
                        voteButton.classList.add('voted');
                    }
                } catch (error) { 
                    console.error(error);
                    showNotification('Ошибка голосования');
                } finally {
                    voteButton.disabled = false;
                }
                return;
            }

            if (target.classList.contains('show-replies-btn')) {
                const parentId = target.dataset.parentId;
                const repliesContainer = document.getElementById(`replies-for-${parentId}`);
                if (repliesContainer.style.display === 'block') {
                    repliesContainer.style.display = 'none';
                    const currentCount = repliesContainer.querySelectorAll('.review-card').length;
                    target.textContent = `💬 Показать ответы (${currentCount})`;
                } else {
                    try {
                        const response = await fetch(`${API_BASE_URL}/get-replies?parent_id=${parentId}&user_id=${userId}`);
                        const replies = await response.json();
                        repliesContainer.innerHTML = replies.map(createReviewHTML).join('');
                        repliesContainer.style.display = 'block';
                        target.textContent = '⬆ Скрыть ответы';
                    } catch (error) {
                        console.error("Не удалось загрузить ответы:", error);
                        repliesContainer.innerHTML = '<p style="font-size: 0.9rem; color: #999; margin-top: 0.5rem;">Не удалось загрузить ответы.</p>';
                        repliesContainer.style.display = 'block';
                    }
                }
            }

            if (target.classList.contains('reply-btn') && !target.classList.contains('show-replies-btn')) {
                const parentId = target.dataset.parentId;
                const authorToReply = target.dataset.author;
                const formContainer = document.getElementById(`reply-form-for-${parentId}`);
                if (formContainer.innerHTML) {
                    formContainer.style.display = formContainer.style.display === 'block' ? 'none' : 'block';
                    return;
                }
                formContainer.innerHTML = `
                    <form class="reply-form">
                        <div class="form-group"><input type="text" class="reply-name" placeholder="Ваше имя" required maxlength="50"></div>
                        <div class="form-group"><textarea placeholder="Напишите ваш ответ..." rows="3" required maxlength="2000">@${authorToReply}, </textarea></div>
                        <div class="reply-form-buttons">
                            <button type="button" class="btn btn-secondary cancel-reply-btn">Отмена</button>
                            <button type="submit" class="btn">Отправить</button>
                        </div>
                    </form>
                `;
                formContainer.style.display = 'block';
                formContainer.querySelector('textarea').focus();
                formContainer.querySelector('.cancel-reply-btn').addEventListener('click', () => {
                    formContainer.style.display = 'none';
                    formContainer.innerHTML = '';
                });
                formContainer.querySelector('.reply-form').addEventListener('submit', async (submitEvent) => {
                    submitEvent.preventDefault();
                    const form = submitEvent.target;
                    const name = form.querySelector('.reply-name').value;
                    const text = form.querySelector('textarea').value;
                    if (text.trim() === '' || name.trim() === '') return;
                    try {
                        const response = await fetch(`${API_BASE_URL}/add-review`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ name: name.trim(), text: text, parent_id: parentId })
                        });
                        const result = await response.json();
                        if (!response.ok) throw new Error(result.message || 'Ошибка сервера');
                        
                        formContainer.innerHTML = '';
                        formContainer.style.display = 'none';
                        
                        if (result.review) {
                            showNotification('Ваш ответ опубликован!');
                            const repliesContainer = document.getElementById(`replies-for-${parentId}`);
                            if (repliesContainer.style.display !== 'block') {
                                const showRepliesBtn = target.closest('.review-card').querySelector('.show-replies-btn');
                                if (showRepliesBtn) {
                                    showRepliesBtn.click();
                                } else {
                                    fetchAndRenderReviews(currentPage);
                                }
                            } else {
                                const newReplyHTML = createReviewHTML(result.review);
                                repliesContainer.insertAdjacentHTML('beforeend', newReplyHTML);
                            }
                        } else {
                            showNotification('Ваш ответ отправлен на модерацию!');
                        }
                    } catch (error) { showNotification(`Ошибка: ${error.message}`); }
                });
            }
        });

        // ПРАВИЛЬНОЕ МЕСТО ДЛЯ ЭТИХ ОБРАБОТЧИКОВ
        const handlePaginationClick = (e) => {
            const target = e.target.closest('.pagination-btn');
            if (target) {
                const page = parseInt(target.dataset.page, 10);
                fetchAndRenderReviews(page);
                const reviewsListTop = document.querySelector('.reviews-list').offsetTop;
                window.scrollTo({ top: reviewsListTop - 100, behavior: 'smooth' });
            }
        };

        if(paginationTop) paginationTop.addEventListener('click', handlePaginationClick);
        if(paginationBottom) paginationBottom.addEventListener('click', handlePaginationClick);
        
        sortSelect.addEventListener('change', () => fetchAndRenderReviews(1));
        
        // Первоначальная загрузка отзывов
        fetchAndRenderReviews();
    }
});