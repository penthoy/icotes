import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from 'react-query';
import axios from 'axios';
import styled from 'styled-components';
import { FiStar, FiUser, FiMapPin, FiClock, FiRefreshCw } from 'react-icons/fi';

const GigContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
`;

const GigHeader = styled.div`
  margin-bottom: 2rem;
`;

const GigTitle = styled.h1`
  font-size: 2.5rem;
  color: ${props => props.theme.secondary};
  margin-bottom: 1rem;
`;

const SellerInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
`;

const SellerAvatar = styled.img`
  width: 50px;
  height: 50px;
  border-radius: 50%;
`;

const SellerDetails = styled.div`
  h3 {
    margin: 0;
    color: ${props => props.theme.secondary};
  }
  p {
    margin: 0;
    color: ${props => props.theme.text};
    font-size: 0.9rem;
  }
`;

const GigContent = styled.div`
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 3rem;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;

const GigImages = styled.div`
  margin-bottom: 2rem;
`;

const MainImage = styled.img`
  width: 100%;
  height: 400px;
  object-fit: cover;
  border-radius: 8px;
  margin-bottom: 1rem;
`;

const ImageGallery = styled.div`
  display: flex;
  gap: 0.5rem;
  overflow-x: auto;
`;

const Thumbnail = styled.img`
  width: 80px;
  height: 60px;
  object-fit: cover;
  border-radius: 4px;
  cursor: pointer;
  border: 2px solid transparent;

  &:hover {
    border-color: ${props => props.theme.primary};
  }
`;

const GigDescription = styled.div`
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
`;

const DescriptionTitle = styled.h2`
  color: ${props => props.theme.secondary};
  margin-bottom: 1rem;
`;

const PricingSection = styled.div`
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 100px;
`;

const PackageCard = styled.div`
  border: 1px solid ${props => props.theme.border};
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;

  &.recommended {
    border-color: ${props => props.theme.primary};
    border-width: 2px;
  }
`;

const PackageHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
`;

const PackageName = styled.h3`
  margin: 0;
  color: ${props => props.theme.secondary};
`;

const PackagePrice = styled.div`
  font-size: 1.5rem;
  font-weight: bold;
  color: ${props => props.theme.primary};
`;

const PackageFeatures = styled.ul`
  list-style: none;
  padding: 0;
  margin-bottom: 1rem;
`;

const PackageFeature = styled.li`
  padding: 0.25rem 0;
  color: ${props => props.theme.text};

  &:before {
    content: '✓';
    color: ${props => props.theme.primary};
    margin-right: 0.5rem;
  }
`;

const ContinueButton = styled.button`
  width: 100%;
  padding: 1rem;
  background: ${props => props.theme.primary};
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.3s ease;

  &:hover {
    background: ${props => props.theme.primaryHover};
  }
`;

const GigDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [selectedPackage, setSelectedPackage] = React.useState('basic');

  const { data: gig, isLoading, error } = useQuery(
    ['gig', id],
    () => axios.get(`/api/gigs/${id}`).then(res => res.data)
  );

  if (isLoading) return <div className="loading">Loading gig details...</div>;
  if (error) return <div className="error">Error loading gig</div>;
  if (!gig) return <div className="error">Gig not found</div>;

  const handleContinue = () => {
    navigate(`/orders/create?gigId=${gig._id}&package=${selectedPackage}`);
  };

  const packages = [
    { key: 'basic', data: gig.pricing.basic, recommended: false },
    { key: 'standard', data: gig.pricing.standard, recommended: true },
    { key: 'premium', data: gig.pricing.premium, recommended: false }
  ];

  return (
    <GigContainer>
      <GigHeader>
        <GigTitle>{gig.title}</GigTitle>
        <SellerInfo>
          {gig.userId?.profilePicture ? (
            <SellerAvatar src={gig.userId.profilePicture} alt={gig.userId.username} />
          ) : (
            <div style={{ 
              width: 50, 
              height: 50, 
              borderRadius: '50%', 
              background: '#ddd',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '20px',
              color: '#666'
            }}>
              {gig.userId?.username?.charAt(0)?.toUpperCase() || 'U'}
            </div>
          )}
          <SellerDetails>
            <h3>{gig.userId?.username}</h3>
            <p>
              <FiMapPin style={{ marginRight: '0.25rem' }} />
              {gig.userId?.country}
            </p>
            <p>
              <FiStar style={{ marginRight: '0.25rem', color: '#ffb33e' }} />
              {gig.userId?.rating} ({gig.userId?.totalReviews} reviews)
            </p>
          </SellerDetails>
        </SellerInfo>
      </GigHeader>

      <GigContent>
        <div>
          <GigImages>
            <MainImage 
              src={gig.images[0] || '/placeholder-gig.jpg'} 
              alt={gig.title}
            />
            {gig.images.length > 1 && (
              <ImageGallery>
                {gig.images.map((image, index) => (
                  <Thumbnail 
                    key={index} 
                    src={image} 
                    alt={`${gig.title} ${index + 1}`}
                  />
                ))}
              </ImageGallery>
            )}
          </GigImages>

          <GigDescription>
            <DescriptionTitle>About This Gig</DescriptionTitle>
            <p style={{ whiteSpace: 'pre-wrap', color: '#666' }}>
              {gig.description}
            </p>
          </GigDescription>
        </div>

        <div>
          <PricingSection>
            <h3 style={{ marginBottom: '1.5rem', color: '#333' }}>Choose Your Package</h3>
            {packages.map(({ key, data, recommended }) => (
              <PackageCard 
                key={key} 
                className={recommended ? 'recommended' : ''}
                onClick={() => setSelectedPackage(key)}
                style={{ cursor: 'pointer' }}
              >
                <PackageHeader>
                  <PackageName>{data.name}</PackageName>
                  <PackagePrice>${data.price}</PackagePrice>
                </PackageHeader>
                <p style={{ color: '#666', marginBottom: '1rem' }}>{data.description}</p>
                <PackageFeatures>
                  <PackageFeature>
                    <FiClock style={{ marginRight: '0.5rem' }} />
                    {data.deliveryTime} day delivery
                  </PackageFeature>
                  <PackageFeature>
                    <FiRefreshCw style={{ marginRight: '0.5rem' }} />
                    {data.revisions} revision{data.revisions !== 1 ? 's' : ''}
                  </PackageFeature>
                  {data.features?.map((feature, index) => (
                    <PackageFeature key={index}>{feature}</PackageFeature>
                  ))}
                </PackageFeatures>
              </PackageCard>
            ))}
            
            <ContinueButton onClick={handleContinue}>
              Continue (${packages.find(p => p.key === selectedPackage)?.data.price})
            </ContinueButton>
          </PricingSection>
        </div>
      </GigContent>
    </GigContainer>
  );
};

export default GigDetails;