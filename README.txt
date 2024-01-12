sudo service mysql start
mysql -u root -p

CREATE DATABASE bbdd_imagenes;
CREATE USER operario@'localhost' IDENTIFIED BY 'oper24';
GRANT ALL PRIVILEGES ON bbdd_imagenes.* TO 'operario'@'localhost';
FLUSH PRIVILEGES;
		
USE bbdd_imagenes;

CREATE TABLE IF NOT EXISTS tabla_inferencias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp TIMESTAMP,
    imagen VARCHAR(255),
    estado ENUM(‘OK’, ‘KO’) NOT NULL
);

Creo estas carpetas:
	inferencias: contendrá las imagenes captadas por la camara con formato "prefijo"timestamp.png
	correcciones: imagenes corregidas con formato "prefijo"timestamp.png
	
