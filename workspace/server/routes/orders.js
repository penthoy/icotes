const express = require('express');
const Order = require('../models/Order');
const Gig = require('../models/Gig');
const auth = require('../middleware/auth');

const router = express.Router();

// Create order
router.post('/', auth, async (req, res) => {
  try {
    const { gigId, package: packageType, requirements } = req.body;

    const gig = await Gig.findById(gigId).populate('userId');
    if (!gig) {
      return res.status(404).json({ message: 'Gig not found' });
    }

    const packageData = gig.pricing[packageType];
    if (!packageData) {
      return res.status(400).json({ message: 'Invalid package type' });
    }

    const deliveryDate = new Date();
    deliveryDate.setDate(deliveryDate.getDate() + packageData.deliveryTime);

    const order = new Order({
      gigId,
      sellerId: gig.userId._id,
      buyerId: req.user.userId,
      package: packageType,
      title: gig.title,
      price: packageData.price,
      requirements,
      deliveryDate,
      maxRevisions: packageData.revisions
    });

    await order.save();

    // Update gig stats
    gig.totalOrders += 1;
    gig.ordersInQueue += 1;
    await gig.save();

    res.status(201).json({
      message: 'Order created successfully',
      order
    });
  } catch (error) {
    console.error('Create order error:', error);
    res.status(500).json({ message: 'Error creating order' });
  }
});

// Get user's orders (as buyer or seller)
router.get('/', auth, async (req, res) => {
  try {
    const { type = 'buyer' } = req.query;
    
    const query = type === 'seller' 
      ? { sellerId: req.user.userId }
      : { buyerId: req.user.userId };

    const orders = await Order.find(query)
      .populate('gigId', 'title images')
      .populate('sellerId', 'username profilePicture')
      .populate('buyerId', 'username profilePicture')
      .sort({ createdAt: -1 });

    res.json(orders);
  } catch (error) {
    console.error('Get orders error:', error);
    res.status(500).json({ message: 'Error fetching orders' });
  }
});

// Get single order
router.get('/:id', auth, async (req, res) => {
  try {
    const order = await Order.findById(req.params.id)
      .populate('gigId')
      .populate('sellerId', 'username profilePicture')
      .populate('buyerId', 'username profilePicture');

    if (!order) {
      return res.status(404).json({ message: 'Order not found' });
    }

    // Check if user is authorized to view this order
    if (order.sellerId._id.toString() !== req.user.userId && 
        order.buyerId._id.toString() !== req.user.userId) {
      return res.status(403).json({ message: 'Unauthorized' });
    }

    res.json(order);
  } catch (error) {
    console.error('Get order error:', error);
    res.status(500).json({ message: 'Error fetching order' });
  }
});

// Send message
router.post('/:id/messages', auth, async (req, res) => {
  try {
    const { message, attachment } = req.body;
    const order = await Order.findById(req.params.id);

    if (!order) {
      return res.status(404).json({ message: 'Order not found' });
    }

    // Check if user is authorized
    if (order.sellerId.toString() !== req.user.userId && 
        order.buyerId.toString() !== req.user.userId) {
      return res.status(403).json({ message: 'Unauthorized' });
    }

    order.messages.push({
      sender: req.user.userId,
      message,
      attachment
    });

    await order.save();

    res.json({ message: 'Message sent successfully' });
  } catch (error) {
    console.error('Send message error:', error);
    res.status(500).json({ message: 'Error sending message' });
  }
});

// Deliver order
router.post('/:id/deliver', auth, async (req, res) => {
  try {
    const { message, attachment } = req.body;
    const order = await Order.findById(req.params.id);

    if (!order) {
      return res.status(404).json({ message: 'Order not found' });
    }

    // Check if user is the seller
    if (order.sellerId.toString() !== req.user.userId) {
      return res.status(403).json({ message: 'Unauthorized' });
    }

    order.deliveries.push({
      message,
      attachment
    });

    order.status = 'delivered';
    await order.save();

    res.json({ message: 'Order delivered successfully' });
  } catch (error) {
    console.error('Deliver order error:', error);
    res.status(500).json({ message: 'Error delivering order' });
  }
});

// Complete order
router.post('/:id/complete', auth, async (req, res) => {
  try {
    const { rating, comment } = req.body;
    const order = await Order.findById(req.params.id);

    if (!order) {
      return res.status(404).json({ message: 'Order not found' });
    }

    // Check if user is the buyer
    if (order.buyerId.toString() !== req.user.userId) {
      return res.status(403).json({ message: 'Unauthorized' });
    }

    order.status = 'completed';
    order.review = {
      rating,
      comment,
      timestamp: new Date()
    };

    await order.save();

    // Update gig stats
    const gig = await Gig.findById(order.gigId);
    if (gig) {
      gig.ordersInQueue -= 1;
      await gig.save();
    }

    res.json({ message: 'Order completed successfully' });
  } catch (error) {
    console.error('Complete order error:', error);
    res.status(500).json({ message: 'Error completing order' });
  }
});

module.exports = router;