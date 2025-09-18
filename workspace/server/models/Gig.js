const mongoose = require('mongoose');

const gigSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  title: {
    type: String,
    required: true,
    maxlength: 100
  },
  description: {
    type: String,
    required: true,
    maxlength: 1000
  },
  category: {
    type: String,
    required: true,
    enum: ['graphics-design', 'digital-marketing', 'writing-translation', 'video-animation', 'music-audio', 'programming', 'business', 'lifestyle']
  },
  subCategory: {
    type: String,
    required: true
  },
  tags: [{
    type: String,
    maxlength: 20
  }],
  pricing: {
    basic: {
      name: {
        type: String,
        default: 'Basic'
      },
      description: String,
      deliveryTime: {
        type: Number,
        required: true
      },
      revisions: {
        type: Number,
        default: 1
      },
      features: [String],
      price: {
        type: Number,
        required: true,
        min: 5
      }
    },
    standard: {
      name: {
        type: String,
        default: 'Standard'
      },
      description: String,
      deliveryTime: {
        type: Number,
        required: true
      },
      revisions: {
        type: Number,
        default: 2
      },
      features: [String],
      price: {
        type: Number,
        required: true,
        min: 5
      }
    },
    premium: {
      name: {
        type: String,
        default: 'Premium'
      },
      description: String,
      deliveryTime: {
        type: Number,
        required: true
      },
      revisions: {
        type: Number,
        default: 3
      },
      features: [String],
      price: {
        type: Number,
        required: true,
        min: 5
      }
    }
  },
  images: [{
    type: String,
    required: true
  }],
  video: {
    type: String,
    default: ''
  },
  faq: [{
    question: String,
    answer: String
  }],
  requirements: [{
    type: {
      type: String,
      enum: ['text', 'multiple', 'attachment'],
      required: true
    },
    question: String,
    required: {
      type: Boolean,
      default: true
    }
  }],
  rating: {
    type: Number,
    min: 0,
    max: 5,
    default: 0
  },
  totalReviews: {
    type: Number,
    default: 0
  },
  totalOrders: {
    type: Number,
    default: 0
  },
  impressions: {
    type: Number,
    default: 0
  },
  clicks: {
    type: Number,
    default: 0
  },
  ordersInQueue: {
    type: Number,
    default: 0
  },
  isActive: {
    type: Boolean,
    default: true
  }
}, {
  timestamps: true
});

gigSchema.index({ title: 'text', description: 'text', tags: 'text' });
gigSchema.index({ category: 1, subCategory: 1 });
gigSchema.index({ rating: -1 });
gigSchema.index({ createdAt: -1 });

module.exports = mongoose.model('Gig', gigSchema);