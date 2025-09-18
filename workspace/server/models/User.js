const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

const userSchema = new mongoose.Schema({
  username: {
    type: String,
    required: true,
    unique: true,
    trim: true,
    minlength: 3,
    maxlength: 30
  },
  email: {
    type: String,
    required: true,
    unique: true,
    lowercase: true,
    trim: true
  },
  password: {
    type: String,
    required: true,
    minlength: 6
  },
  profilePicture: {
    type: String,
    default: ''
  },
  country: {
    type: String,
    required: true
  },
  isSeller: {
    type: Boolean,
    default: false
  },
  description: {
    type: String,
    maxlength: 500
  },
  skills: [{
    type: String,
    maxlength: 50
  }],
  languages: [{
    language: String,
    level: {
      type: String,
      enum: ['basic', 'conversational', 'fluent', 'native']
    }
  }],
  education: [{
    school: String,
    degree: String,
    startYear: Number,
    endYear: Number
  }],
  certifications: [{
    name: String,
    from: String,
    year: Number
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
  earnings: {
    type: Number,
    default: 0
  },
  responseTime: {
    type: Number,
    default: 0
  },
  recentDelivery: {
    type: Date
  },
  memberSince: {
    type: Date,
    default: Date.now
  }
}, {
  timestamps: true
});

userSchema.pre('save', async function(next) {
  if (!this.isModified('password')) return next();
  
  try {
    const salt = await bcrypt.genSalt(10);
    this.password = await bcrypt.hash(this.password, salt);
    next();
  } catch (error) {
    next(error);
  }
});

userSchema.methods.comparePassword = async function(candidatePassword) {
  return await bcrypt.compare(candidatePassword, this.password);
};

module.exports = mongoose.model('User', userSchema);