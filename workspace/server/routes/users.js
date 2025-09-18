const express = require('express');
const User = require('../models/User');
const auth = require('../middleware/auth');

const router = express.Router();

// Get user profile
router.get('/:id', async (req, res) => {
  try {
    const user = await User.findById(req.params.id).select('-password');
    
    if (!user) {
      return res.status(404).json({ message: 'User not found' });
    }

    res.json(user);
  } catch (error) {
    console.error('Get user error:', error);
    res.status(500).json({ message: 'Error fetching user' });
  }
});

// Get top sellers
router.get('/sellers/top', async (req, res) => {
  try {
    const { limit = 10 } = req.query;
    
    const sellers = await User.find({ 
      isSeller: true,
      rating: { $gte: 4.5 }
    })
    .select('-password')
    .sort({ rating: -1, totalReviews: -1 })
    .limit(Number(limit));

    res.json(sellers);
  } catch (error) {
    console.error('Get top sellers error:', error);
    res.status(500).json({ message: 'Error fetching top sellers' });
  }
});

// Become a seller
router.post('/become-seller', auth, async (req, res) => {
  try {
    const user = await User.findById(req.user.userId);
    
    if (!user) {
      return res.status(404).json({ message: 'User not found' });
    }

    if (user.isSeller) {
      return res.status(400).json({ message: 'User is already a seller' });
    }

    const { description, skills, languages } = req.body;

    user.isSeller = true;
    user.description = description;
    user.skills = skills;
    user.languages = languages;

    await user.save();

    res.json({
      message: 'Successfully became a seller',
      user: user.select('-password')
    });
  } catch (error) {
    console.error('Become seller error:', error);
    res.status(500).json({ message: 'Error becoming seller' });
  }
});

module.exports = router;