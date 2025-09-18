# Fiverr Clone - Freelance Services Marketplace

A full-stack demo application that replicates the core functionality of Fiverr.com, built with React.js, Node.js, Express, and MongoDB.

## Features

### User Features
- 📝 User registration and authentication
- 👤 User profiles with seller/buyer roles
- 🔍 Search and filter services by category, price, delivery time
- ⭐ Rating and review system
- 💬 Messaging system between buyers and sellers
- 📦 Order management system
- 🛒 Three-tier pricing packages (Basic, Standard, Premium)

### Seller Features
- 🎨 Create and manage service listings (Gigs)
- 📊 Track orders and earnings
- 💬 Communicate with buyers
- 📈 View gig analytics and performance

### Buyer Features
- 🔎 Browse and search for services
- 📋 Place orders with custom requirements
- 💬 Communicate with sellers
- ⭐ Rate and review completed orders

## Tech Stack

### Frontend
- React.js 18
- React Router v6
- Styled Components
- React Query for data fetching
- Axios for API calls
- React Hook Form for form handling

### Backend
- Node.js
- Express.js
- MongoDB with Mongoose
- JWT Authentication
- Bcrypt for password hashing
- Multer for file uploads

## Installation

### Prerequisites
- Node.js (v14 or higher)
- MongoDB (local or cloud instance)
- npm or yarn

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fiverr-clone
   ```

2. **Install dependencies**
   ```bash
   npm run install-all
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   NODE_ENV=development
   PORT=5000
   MONGODB_URI=mongodb://localhost:27017/fiverr-clone
   JWT_SECRET=your-super-secret-jwt-key
   ```

   Create a `.env` file in the client directory:
   ```env
   REACT_APP_API_URL=http://localhost:5000
   ```

4. **Start MongoDB**
   Make sure MongoDB is running on your system.

5. **Seed the database (optional)**
   ```bash
   node scripts/seedData.js
   ```

6. **Start the development servers**
   ```bash
   npm run dev
   ```
   
   This will start both the backend server (port 5000) and the React development server (port 3000).

## Usage

### Default Users
After running the seed script, you can log in with these test accounts:

**Sellers:**
- designer@example.com / password123
- developer@example.com / password123
- writer@example.com / password123
- editor@example.com / password123

**Buyer:**
- buyer@example.com / password123

### Key Pages
- **Homepage**: Browse featured services and categories
- **Search**: Filter and search for services
- **Gig Details**: View service details and pricing packages
- **Profile**: User profile with services and reviews
- **Orders**: Manage orders (for both buyers and sellers)
- **Create Gig**: Create new service listings (sellers only)

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user

### Gigs
- `GET /api/gigs` - Get all gigs (with filtering)
- `GET /api/gigs/:id` - Get single gig
- `POST /api/gigs` - Create new gig (protected)
- `PUT /api/gigs/:id` - Update gig (protected)
- `DELETE /api/gigs/:id` - Delete gig (protected)

### Users
- `GET /api/users/:id` - Get user profile
- `GET /api/users/sellers/top` - Get top sellers

### Orders
- `GET /api/orders` - Get user orders (protected)
- `POST /api/orders` - Create order (protected)
- `GET /api/orders/:id` - Get order details (protected)
- `POST /api/orders/:id/messages` - Send message (protected)
- `POST /api/orders/:id/deliver` - Deliver order (protected)
- `POST /api/orders/:id/complete` - Complete order (protected)

## Project Structure

```
fiverr-clone/
├── client/                 # React frontend
│   ├── public/
│   ├── src/
│   │   ├── components/     # Reusable components
│   │   ├── pages/         # Page components
│   │   ├── contexts/      # React contexts
│   │   ├── styles/        # Global styles
│   │   └── App.js         # Main app component
│   └── package.json
├── server/                 # Node.js backend
│   ├── models/            # MongoDB models
│   ├── routes/            # API routes
│   ├── middleware/        # Custom middleware
│   └── index.js           # Server entry point
├── scripts/               # Utility scripts
└── package.json
```

## Features to Add

This is a demo application with core functionality. Here are some features that could be added:

- [ ] Real-time messaging with WebSocket
- [ ] File upload functionality
- [ ] Payment integration (Stripe/PayPal)
- [ ] Email notifications
- [ ] Advanced search with Elasticsearch
- [ ] Admin dashboard
- [ ] Mobile app (React Native)
- [ ] Video calling for consultations
- [ ] Subscription plans
- [ ] Advanced analytics
- [ ] Multi-language support

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This is a demo project created for educational purposes only. It is not intended for production use and does not include all the features, security measures, and optimizations of the real Fiverr platform.

## Support

If you have any questions or need help with the project, feel free to open an issue or contact the maintainers.

---

**Note**: This is a demonstration project showcasing full-stack development skills. The design and functionality are inspired by Fiverr but implemented independently for learning purposes.