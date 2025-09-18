const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const User = require('../server/models/User');
const Gig = require('../server/models/Gig');

const seedData = async () => {
  try {
    // Connect to MongoDB
    await mongoose.connect('mongodb://localhost:27017/fiverr-clone', {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    });

    console.log('Connected to MongoDB');

    // Clear existing data
    await User.deleteMany({});
    await Gig.deleteMany({});

    console.log('Cleared existing data');

    // Create sample users
    const users = [
      {
        username: 'design_pro',
        email: 'designer@example.com',
        password: 'password123',
        country: 'United States',
        isSeller: true,
        description: 'Professional graphic designer with 5+ years of experience in logo design and branding.',
        skills: ['Logo Design', 'Branding', 'Adobe Illustrator', 'Photoshop'],
        languages: [{ language: 'English', level: 'native' }],
        rating: 4.8,
        totalReviews: 127,
        earnings: 15420
      },
      {
        username: 'web_dev_master',
        email: 'developer@example.com',
        password: 'password123',
        country: 'United Kingdom',
        isSeller: true,
        description: 'Full-stack web developer specializing in React, Node.js, and modern web technologies.',
        skills: ['React', 'Node.js', 'JavaScript', 'MongoDB', 'Express'],
        languages: [{ language: 'English', level: 'native' }],
        rating: 4.9,
        totalReviews: 89,
        earnings: 22150
      },
      {
        username: 'content_writer',
        email: 'writer@example.com',
        password: 'password123',
        country: 'Canada',
        isSeller: true,
        description: 'Experienced content writer and copywriter with expertise in SEO and digital marketing.',
        skills: ['Content Writing', 'SEO', 'Copywriting', 'Blog Writing'],
        languages: [{ language: 'English', level: 'native' }],
        rating: 4.7,
        totalReviews: 203,
        earnings: 18900
      },
      {
        username: 'video_editor',
        email: 'editor@example.com',
        password: 'password123',
        country: 'Australia',
        isSeller: true,
        description: 'Creative video editor and motion graphics artist with 7 years of experience.',
        skills: ['Video Editing', 'Motion Graphics', 'After Effects', 'Premiere Pro'],
        languages: [{ language: 'English', level: 'native' }],
        rating: 4.6,
        totalReviews: 156,
        earnings: 12800
      },
      {
        username: 'buyer_john',
        email: 'buyer@example.com',
        password: 'password123',
        country: 'United States',
        isSeller: false
      }
    ];

    // Hash passwords and create users
    const createdUsers = [];
    for (const userData of users) {
      const hashedPassword = await bcrypt.hash(userData.password, 10);
      const user = new User({
        ...userData,
        password: hashedPassword
      });
      await user.save();
      createdUsers.push(user);
      console.log(`Created user: ${user.username}`);
    }

    // Create sample gigs
    const gigs = [
      {
        userId: createdUsers[0]._id,
        title: 'I will design a professional logo for your business',
        description: 'Looking for a unique and professional logo that represents your brand perfectly? I specialize in creating custom logos that are memorable, scalable, and versatile. My designs are modern, clean, and tailored to your specific industry and target audience.\n\nWhat you get:\n- 3 unique logo concepts\n- High-resolution files (PNG, JPG, PDF)\n- Vector files (AI, EPS, SVG)\n- Unlimited revisions\n- 100% satisfaction guarantee\n\nI have worked with over 100+ businesses across various industries and have a proven track record of delivering exceptional results. Let me help you create a logo that will make your brand stand out!',
        category: 'graphics-design',
        subCategory: 'logo-design',
        tags: ['logo', 'branding', 'design', 'business', 'professional'],
        pricing: {
          basic: {
            name: 'Basic',
            description: 'Simple logo design with 2 concepts',
            deliveryTime: 3,
            revisions: 2,
            features: ['2 logo concepts', 'PNG & JPG files', 'Basic color palette'],
            price: 25
          },
          standard: {
            name: 'Standard',
            description: 'Professional logo with 3 concepts and brand guide',
            deliveryTime: 5,
            revisions: 3,
            features: ['3 logo concepts', 'Vector files included', 'Brand color palette', 'Typography suggestions'],
            price: 75
          },
          premium: {
            name: 'Premium',
            description: 'Complete brand identity package',
            deliveryTime: 7,
            revisions: 5,
            features: ['5 logo concepts', 'Complete brand guide', 'Business card design', 'Social media kit', 'Vector files'],
            price: 150
          }
        },
        images: ['https://via.placeholder.com/800x600/1dbf73/ffffff?text=Logo+Design+1'],
        rating: 4.8,
        totalReviews: 127,
        totalOrders: 203
      },
      {
        userId: createdUsers[1]._id,
        title: 'I will build a responsive website with React and Node.js',
        description: 'Need a modern, responsive website that looks great on all devices? I specialize in building fast, scalable web applications using React, Node.js, and MongoDB. Whether you need a simple landing page or a complex web application, I can deliver exactly what you need.\n\nMy expertise includes:\n- React.js & Next.js\n- Node.js & Express.js\n- MongoDB & Mongoose\n- RESTful APIs\n- Authentication & Authorization\n- Responsive Design\n- SEO Optimization\n\nI follow best practices for clean code, performance optimization, and security. Your website will be fast, secure, and easy to maintain.',
        category: 'programming',
        subCategory: 'web-development',
        tags: ['react', 'nodejs', 'website', 'responsive', 'mongodb'],
        pricing: {
          basic: {
            name: 'Basic',
            description: 'Simple landing page with basic features',
            deliveryTime: 7,
            revisions: 2,
            features: ['1-page website', 'Responsive design', 'Basic contact form', 'SEO optimized'],
            price: 150
          },
          standard: {
            name: 'Standard',
            description: 'Multi-page website with CMS integration',
            deliveryTime: 14,
            revisions: 3,
            features: ['Up to 5 pages', 'CMS integration', 'User authentication', 'Admin panel', 'Contact forms'],
            price: 500
          },
          premium: {
            name: 'Premium',
            description: 'Full-stack web application with advanced features',
            deliveryTime: 21,
            revisions: 5,
            features: ['Custom web app', 'Database integration', 'User management', 'Payment processing', 'Admin dashboard', 'API development'],
            price: 1200
          }
        },
        images: ['https://via.placeholder.com/800x600/764ba2/ffffff?text=Web+Development'],
        rating: 4.9,
        totalReviews: 89,
        totalOrders: 156
      },
      {
        userId: createdUsers[2]._id,
        title: 'I will write engaging blog posts and articles',
        description: 'Looking for high-quality, engaging content that ranks well in search engines? I am a professional content writer with expertise in creating compelling blog posts, articles, and website content that drives traffic and conversions.\n\nWhat I offer:\n- Well-researched, original content\n- SEO optimization\n- Engaging headlines and subheadings\n- Proper formatting and structure\n- Grammar and spell-check\n- Unlimited revisions\n- Fast delivery\n\nI can write on various topics including technology, business, health, lifestyle, travel, and more. All content is 100% original and passes plagiarism checks.',
        category: 'writing-translation',
        subCategory: 'article-writing',
        tags: ['content writing', 'blog posts', 'SEO', 'articles', 'copywriting'],
        pricing: {
          basic: {
            name: 'Basic',
            description: '500-word blog post',
            deliveryTime: 3,
            revisions: 2,
            features: ['500 words', 'SEO optimized', '1 keyword', 'Plagiarism free'],
            price: 30
          },
          standard: {
            name: 'Standard',
            description: '1000-word comprehensive article',
            deliveryTime: 5,
            revisions: 3,
            features: ['1000 words', 'SEO optimized', '2-3 keywords', 'Research included', 'Meta description'],
            price: 60
          },
          premium: {
            name: 'Premium',
            description: '2000-word in-depth article with research',
            deliveryTime: 7,
            revisions: 5,
            features: ['2000 words', 'In-depth research', 'SEO optimized', 'Multiple keywords', 'Images included', 'Social media snippets'],
            price: 120
          }
        },
        images: ['https://via.placeholder.com/800x600/667eea/ffffff?text=Content+Writing'],
        rating: 4.7,
        totalReviews: 203,
        totalOrders: 312
      },
      {
        userId: createdUsers[3]._id,
        title: 'I will edit and enhance your videos professionally',
        description: 'Transform your raw footage into a polished, professional video that captivates your audience. I offer comprehensive video editing services including color correction, audio enhancement, motion graphics, and special effects.\n\nServices include:\n- Professional video editing\n- Color correction and grading\n- Audio enhancement and mixing\n- Motion graphics and titles\n- Transitions and effects\n- Subtitles and captions\n- Format optimization for different platforms\n\nI work with all major video formats and can deliver in any format you need. Whether it\'s a YouTube video, promotional content, wedding video, or corporate presentation, I\'ll make it look amazing!',
        category: 'video-animation',
        subCategory: 'video-editing',
        tags: ['video editing', 'motion graphics', 'color correction', 'audio enhancement', 'YouTube'],
        pricing: {
          basic: {
            name: 'Basic',
            description: 'Simple video editing up to 5 minutes',
            deliveryTime: 3,
            revisions: 2,
            features: ['Up to 5 minutes', 'Basic cuts and transitions', 'Color correction', 'Audio sync'],
            price: 50
          },
          standard: {
            name: 'Standard',
            description: 'Professional editing up to 15 minutes',
            deliveryTime: 5,
            revisions: 3,
            features: ['Up to 15 minutes', 'Advanced editing', 'Color grading', 'Audio enhancement', 'Titles and graphics'],
            price: 120
          },
          premium: {
            name: 'Premium',
            description: 'Full production up to 30 minutes',
            deliveryTime: 7,
            revisions: 5,
            features: ['Up to 30 minutes', 'Full production', 'Advanced color grading', 'Professional audio mix', 'Motion graphics', 'Special effects'],
            price: 250
          }
        },
        images: ['https://via.placeholder.com/800x600/ff6b6b/ffffff?text=Video+Editing'],
        rating: 4.6,
        totalReviews: 156,
        totalOrders: 234
      }
    ];

    // Create gigs
    for (const gigData of gigs) {
      const gig = new Gig(gigData);
      await gig.save();
      console.log(`Created gig: ${gig.title}`);
    }

    console.log('Database seeded successfully!');
    process.exit(0);
  } catch (error) {
    console.error('Error seeding database:', error);
    process.exit(1);
  }
};

// Run the seed function
seedData();