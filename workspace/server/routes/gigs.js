const express = require('express');
const Gig = require('../models/Gig');
const auth = require('../middleware/auth');

const router = express.Router();

// Get all gigs with filtering and pagination
router.get('/', async (req, res) => {
  try {
    const {
      page = 1,
      limit = 12,
      category,
      subCategory,
      minPrice,
      maxPrice,
      deliveryTime,
      search,
      sortBy = 'createdAt',
      sortOrder = 'desc'
    } = req.query;

    const query = { isActive: true };
    
    if (category) query.category = category;
    if (subCategory) query.subCategory = subCategory;
    if (minPrice || maxPrice) {
      query['pricing.basic.price'] = {};
      if (minPrice) query['pricing.basic.price'].$gte = Number(minPrice);
      if (maxPrice) query['pricing.basic.price'].$lte = Number(maxPrice);
    }
    if (deliveryTime) {
      query['pricing.basic.deliveryTime'] = { $lte: Number(deliveryTime) };
    }
    if (search) {
      query.$text = { $search: search };
    }

    const sortOptions = {};
    sortOptions[sortBy] = sortOrder === 'desc' ? -1 : 1;

    const gigs = await Gig.find(query)
      .populate('userId', 'username profilePicture country rating')
      .sort(sortOptions)
      .limit(limit * 1)
      .skip((page - 1) * limit);

    const total = await Gig.countDocuments(query);

    res.json({
      gigs,
      totalPages: Math.ceil(total / limit),
      currentPage: page,
      total
    });
  } catch (error) {
    console.error('Get gigs error:', error);
    res.status(500).json({ message: 'Error fetching gigs' });
  }
});

// Get single gig
router.get('/:id', async (req, res) => {
  try {
    const gig = await Gig.findById(req.params.id)
      .populate('userId', '-password');
    
    if (!gig) {
      return res.status(404).json({ message: 'Gig not found' });
    }

    // Increment impressions
    gig.impressions += 1;
    await gig.save();

    res.json(gig);
  } catch (error) {
    console.error('Get gig error:', error);
    res.status(500).json({ message: 'Error fetching gig' });
  }
});

// Create new gig
router.post('/', auth, async (req, res) => {
  try {
    const gigData = {
      ...req.body,
      userId: req.user.userId
    };

    const gig = new Gig(gigData);
    await gig.save();

    res.status(201).json({
      message: 'Gig created successfully',
      gig
    });
  } catch (error) {
    console.error('Create gig error:', error);
    res.status(500).json({ message: 'Error creating gig' });
  }
});

// Update gig
router.put('/:id', auth, async (req, res) => {
  try {
    const gig = await Gig.findOne({ _id: req.params.id, userId: req.user.userId });
    
    if (!gig) {
      return res.status(404).json({ message: 'Gig not found or unauthorized' });
    }

    Object.assign(gig, req.body);
    await gig.save();

    res.json({
      message: 'Gig updated successfully',
      gig
    });
  } catch (error) {
    console.error('Update gig error:', error);
    res.status(500).json({ message: 'Error updating gig' });
  }
});

// Delete gig
router.delete('/:id', auth, async (req, res) => {
  try {
    const gig = await Gig.findOne({ _id: req.params.id, userId: req.user.userId });
    
    if (!gig) {
      return res.status(404).json({ message: 'Gig not found or unauthorized' });
    }

    gig.isActive = false;
    await gig.save();

    res.json({ message: 'Gig deleted successfully' });
  } catch (error) {
    console.error('Delete gig error:', error);
    res.status(500).json({ message: 'Error deleting gig' });
  }
});

// Get user's gigs
router.get('/user/:userId', async (req, res) => {
  try {
    const gigs = await Gig.find({ 
      userId: req.params.userId, 
      isActive: true 
    })
    .populate('userId', 'username profilePicture country rating')
    .sort({ createdAt: -1 });

    res.json(gigs);
  } catch (error) {
    console.error('Get user gigs error:', error);
    res.status(500).json({ message: 'Error fetching user gigs' });
  }
});

module.exports = router;