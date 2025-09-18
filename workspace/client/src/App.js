import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { ThemeProvider } from 'styled-components';
import Header from './components/Header';
import Footer from './components/Footer';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import GigDetails from './pages/GigDetails';
import CreateGig from './pages/CreateGig';
import Profile from './pages/Profile';
import Orders from './pages/Orders';
import Search from './pages/Search';
import ProtectedRoute from './components/ProtectedRoute';
import GlobalStyles from './styles/GlobalStyles';

const theme = {
  primary: '#1dbf73',
  primaryHover: '#19a463',
  secondary: '#404145',
  text: '#62646a',
  border: '#dadbdd',
  success: '#1dbf73',
  warning: '#ffb33e',
  error: '#ff3838',
  white: '#ffffff',
  black: '#000000',
};

function App() {
  return (
    <ThemeProvider theme={theme}>
      <GlobalStyles />
      <div className="App">
        <Header />
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/gig/:id" element={<GigDetails />} />
            <Route path="/search" element={<Search />} />
            <Route path="/user/:id" element={<Profile />} />
            
            {/* Protected Routes */}
            <Route
              path="/create-gig"
              element={
                <ProtectedRoute>
                  <CreateGig />
                </ProtectedRoute>
              }
            />
            <Route
              path="/orders"
              element={
                <ProtectedRoute>
                  <Orders />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <Profile />
                </ProtectedRoute>
              }
            />
          </Routes>
        </main>
        <Footer />
      </div>
    </ThemeProvider>
  );
}

export default App;