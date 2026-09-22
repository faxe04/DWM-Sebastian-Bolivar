import './App.css'
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { NavBar } from './components/NavBar/NavBar.jsx';
import { Footer } from './components/Footer/Footer.jsx';
import { HomePage } from './pages/HomePage.jsx'
import { ProductsPage } from './pages/Products/ProductsPage.jsx';
import { AboutPage } from './pages/About/AboutPage.jsx';
import { ContactPage } from './pages/Contact/ContactPage.jsx';
import { LoginPage } from './pages/login/LoginPage.jsx';
import { CartPage } from './pages/Cart/Cartpage.jsx';
import { PaymentApprovedPage } from './pages/PaymentApprovedPage/PaymentApprovedPage.jsx';

function App() {

  return (
    <BrowserRouter>
      <NavBar />
      <main className='main-content'>
        <Routes>
          <Route path='/' element={<HomePage/>} />
          <Route path='/productos' element={<ProductsPage />} />
          <Route path='/nosotros' element={<AboutPage/>} />
          <Route path='/contacto' element={<ContactPage/>} />*/
          <Route path='/login' element={<LoginPage />} /> 
          <Route path='/carrito' element={<CartPage />} />
          <Route path='/pago-aprobado' element={<PaymentApprovedPage />} /> 
        </Routes>
      </main>
      <Footer />
    </BrowserRouter>
  )
}

export default App
