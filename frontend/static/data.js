const categories = [
  {
    label: 'Electronics',
    count: '14,200+ products',
    image: 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=900&q=80'
  },
  {
    label: 'Clothing',
    count: '22,800+ products',
    image: 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=900&q=80'
  },
  {
    label: 'Household',
    count: '11,400+ products',
    image: 'https://images.unsplash.com/photo-1517142089942-ba376ce32a2e?auto=format&fit=crop&w=900&q=80'
  }
];

const products = [
  {
    id: 1,
    name: 'Wireless Headphones',
    category: 'Electronics',
    price: 89.99,
    oldPrice: 149.99,
    rating: 4.7,
    badge: 'sale',
    image: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80',
    description: 'Comfortable over-ear headphones with noise reduction and long battery life.'
  },
  {
    id: 2,
    name: 'Oxford Shirt',
    category: 'Clothing',
    price: 24.99,
    oldPrice: 39.99,
    rating: 4.4,
    badge: 'sale',
    image: 'https://images.unsplash.com/photo-1603252109303-2751441dd157?auto=format&fit=crop&w=900&q=80',
    description: 'Simple slim-fit shirt for casual or smart wear.'
  },
  {
    id: 3,
    name: 'Cookware Set',
    category: 'Household',
    price: 64.99,
    oldPrice: 99.99,
    rating: 4.6,
    badge: 'sale',
    image: 'https://images.unsplash.com/photo-1584990347449-a69f18549a67?auto=format&fit=crop&w=900&q=80',
    description: 'Durable stainless-steel cookware set for everyday cooking.'
  },
  {
    id: 4,
    name: '4K Smart TV',
    category: 'Electronics',
    price: 319.99,
    oldPrice: 499.99,
    rating: 4.5,
    badge: 'sale',
    image: 'https://images.unsplash.com/photo-1593784991095-a205069470b6?auto=format&fit=crop&w=900&q=80',
    description: '43-inch smart TV with streaming apps and high-resolution display.'
  },
  {
    id: 5,
    name: 'Running Trainers',
    category: 'Clothing',
    price: 54.99,
    oldPrice: 79.99,
    rating: 4.8,
    badge: 'new',
    image: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80',
    description: 'Lightweight trainers designed for comfort, gym use and daily wear.'
  },
  {
    id: 6,
    name: 'Cordless Vacuum',
    category: 'Household',
    price: 119.99,
    oldPrice: 179.99,
    rating: 4.3,
    badge: 'sale',
    image: 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=crop&w=900&q=80',
    description: 'Cordless vacuum cleaner with easy charging dock and strong suction.'
  },
  {
    id: 7,
    name: 'Bluetooth Speaker',
    category: 'Electronics',
    price: 39.99,
    oldPrice: 59.99,
    rating: 4.2,
    badge: 'sale',
    image: 'https://images.unsplash.com/photo-1589003077984-894e133dabab?auto=format&fit=crop&w=900&q=80',
    description: 'Portable speaker with Bluetooth connection and waterproof design.'
  },
  {
    id: 8,
    name: 'Storage Basket Set',
    category: 'Household',
    price: 22.99,
    oldPrice: 29.99,
    rating: 4.1,
    badge: 'new',
    image: 'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=900&q=80',
    description: 'Minimal storage baskets for organising rooms and shelves.'
  }
];

const reviews = [
  { name: 'Maya', product: 'Wireless Headphones', rating: 5, text: 'Really good sound and the battery lasted longer than I expected.' },
  { name: 'Jamal', product: 'Running Trainers', rating: 4, text: 'Comfortable and easy to wear all day. Good value.' },
  { name: 'Hannah', product: 'Cookware Set', rating: 5, text: 'Looks clean and works well. Feels better than the cheap set I had before.' }
];
