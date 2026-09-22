import "./ProductsPage.css"
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { products } from "../../services/products";
import { ProductCard } from "../../components/Product/ProductCard";


export function ProductsPage(){
    const [seachParams, setSearchParams] = useSearchParams();
    const [search, setSearch] = useState("");

    const category = seachParams.get("categoria") || "todos";

    const filteredProducts = products.filter(product => {
        const matchesCategory = category === "todos" || product.category == category;
        const matchesSearch = product.name.toLowerCase().includes(search.toLowerCase());
        return matchesCategory && matchesSearch;
    });

    const changeCategory = (newCategory) => {
        if (newCategory === "todos"){
            setSearchParams({});
        } else {
            setSearchParams({ categoria: newCategory });
        }
    }

    return (
        <section className="products-page">
            <div className="products-header">
                <h1>Productos</h1>
                <input 
                    className="product-seach" 
                    type="text" 
                    placeholder="Buscar producto..." 
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                />
            </div>

            <div className="products-filters">
                <button
                    onClick={() => changeCategory("todos")}
                    className={category === "todos" ? "active" : ""}
                >
                    Todos
                </button>

                <button
                    onClick={() => changeCategory("cafe")}
                    className={category === "cafe" ? "active" : ""}
                >
                    Café
                </button>

                <button
                    onClick={() => changeCategory("reposteria")}
                    className={category === "reposteria" ? "active" : ""}
                >
                    Reposteria
                </button>
            </div>
            <div className="products-grid">
                {filteredProducts.map(product => (
                    <ProductCard
                        key={product.id}
                        product={product}
                    />
                ))}
            </div>

        </section>
    )
}

