import cafeEspresso from "../assets/imgs/products/cafe-espresso.png";
import cafeLatte from "../assets/imgs/products/cafe-latte.png";
import cheesecake from "../assets/imgs/products/cheesecake.png";
import brownie from "../assets/imgs/products/brownie.png";

export const products = [
  {
    id: 1,
    name: "Café Espresso",
    category: "cafe",
    price: 2490,
    image: cafeEspresso,
    available: true,
    featured: true,
  },
  {
    id: 2,
    name: "Café Latte",
    category: "cafe",
    price: 2990,
    image: cafeLatte,
    available: true,
    featured: true,
  },
  {
    id: 3,
    name: "Cheesecake Frutos Rojos",
    category: "reposteria",
    price: 3990,
    image: cheesecake,
    available: true,
    featured: true,
  },
  {
    id: 4,
    name: "Brownie de Chocolate",
    category: "reposteria",
    price: 2890,
    image: brownie,
    available: true,
    featured: false,
  },
];