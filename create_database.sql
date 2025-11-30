DROP DATABASE IF EXISTS artstore;
CREATE DATABASE artstore CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE artstore;

CREATE TABLE users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  email VARCHAR(120) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE admins (
  admin_id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  name VARCHAR(100)
);

CREATE TABLE artists (
  artist_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  bio TEXT
);

CREATE TABLE artworks (
  artwork_id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  description TEXT,
  price DECIMAL(10,2) NOT NULL,
  image_filename VARCHAR(255),
  artist_id INT,
  available_qty INT DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (artist_id) REFERENCES artists(artist_id) ON DELETE SET NULL
);

CREATE TABLE orders (
  order_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  total_amount DECIMAL(10,2) NOT NULL,
  status VARCHAR(50) DEFAULT 'Pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE order_items (
  order_item_id INT AUTO_INCREMENT PRIMARY KEY,
  order_id INT NOT NULL,
  artwork_id INT NOT NULL,
  quantity INT NOT NULL,
  unit_price DECIMAL(10,2) NOT NULL,
  FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
  FOREIGN KEY (artwork_id) REFERENCES artworks(artwork_id) ON DELETE CASCADE
);

INSERT INTO admins (username, password, name) VALUES
('admin', 'scrypt:32768:8:1$YViLob8JvMeqQMoz$0959c5bf26b741be2e3d929f8aead903412c60dee5a91daeb5333c644c33575847d7263982eee5070eb8bf507d2d43f80091fde7193eeeda1c05485c38267bd1', 'Gallery Admin');

INSERT INTO artists (name, bio) VALUES
('Ravi Kumar', 'Contemporary painter from India.'),
('Ananya Roy', 'Digital artist focusing on surreal landscapes.'),

INSERT INTO artworks (title, description, price, image_filename, artist_id, available_qty) VALUES
('Sunset over Ganges', 'Oil painting with vibrant hues', 12000.00, 'sunset.jpg', 1, 1),
('Dreamscape #1', 'Digital print, limited edition', 3500.00, 'dream1.jpg', 2, 5);
