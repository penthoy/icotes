const mongoose = require('mongoose');

const orderSchema = new mongoose.Schema({
  gigId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Gig',
    required: true
  },
  sellerId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  buyerId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  package: {
    type: String,
    enum: ['basic', 'standard', 'premium'],
    required: true
  },
  title: {
    type: String,
    required: true
  },
  price: {
    type: Number,
    required: true
  },
  quantity: {
    type: Number,
    default: 1
  },
  requirements: [{
    question: String,
    answer: String,
    attachment: String
  }],
  status: {
    type: String,
    enum: ['pending', 'in-progress', 'delivered', 'completed', 'cancelled', 'disputed'],
    default: 'pending'
  },
  deliveryDate: {
    type: Date,
    required: true
  },
  revisions: {
    type: Number,
    default: 0
  },
  maxRevisions: {
    type: Number,
    default: 1
  },
  messages: [{
    sender: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true
    },
    message: {
      type: String,
      required: true
    },
    attachment: String,
    timestamp: {
      type: Date,
      default: Date.now
    }
  }],
  deliveries: [{
    message: String,
    attachment: String,
    timestamp: {
      type: Date,
      default: Date.now
    }
  }],
  review: {
    rating: {
      type: Number,
      min: 1,
      max: 5
    },
    comment: String,
    timestamp: Date
  },
  paymentStatus: {
    type: String,
    enum: ['pending', 'paid', 'refunded'],
    default: 'pending'
  },
  commission: {
    type: Number,
    default: 0
  },
  earnings: {
    type: Number,
    default: 0
  }
}, {
  timestamps: true
});

module.exports = mongoose.model('Order', orderSchema);