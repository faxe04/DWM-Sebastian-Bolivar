import './HomePage.css'
import { Link } from 'react-router-dom'
import bgImg from "../assets/imgs/cofe1.jpg"
import IconCoffee from '../assets/svgs/IconCoffe'
import IconCupcake from '../assets/svgs/IconCupcake'
import IconDiscount from '../assets/svgs/IconDiscount'
import { products } from "../services/products"
import { ProductCard } from '../components/Product/ProductCard'


export function HomePage() {
  const featuredProducts = products.filter(
    product => product.featured
  );

  return (
    <>
      <section  className="hero">
        <img 
        className="hero-image"
        src={bgImg}
        alt="Cafe"
        />
        <div className="hero-content">
          <p className="hero-label">CAFE & REPOSTERÍA</p>
          <h1>Un momento para disfrutar</h1>
          <p className="hero-description">Café de especialidad y repostería artesanal</p>
        </div>
      </section  >

      <section  className="categories">
        <h2>Categorias</h2>
        <div className="categories-grid">

          <Link className="category-card" to="/productos?categoria=cafe">
            <div className="category-icon">
              <IconCoffee size={30} strokeWidth={5} />
            </div>
            <span>Café</span>
          </Link>

          <Link className="category-card" to="/productos?categoria=reposteria">
            <div className="category-icon">
              <IconCupcake size={33} />
            </div>
            <span>Repostería</span>
          </Link>

          <Link className="category-card" to="/productos?categoria=promociones">
            <div className="category-icon">
              <IconDiscount size={33} />
            </div>
            <span>Promociones</span>
          </Link>
        </div>
      </section >

      <section className='featured-products'>
        <h2>Productos Destacados</h2>
        <div className="products-grid">
          {featuredProducts.map(product => (
            <ProductCard
              key={product.id}
              product={product}
            />
          ))}
        </div>
      </section>
    </>
  )
}