import React from 'react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';
import { FiStar, FiHeart } from 'react-icons/fi';

const Card = styled.div`
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  cursor: pointer;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  }
`;

const ImageContainer = styled.div`
  position: relative;
  height: 200px;
  overflow: hidden;
`;

const GigImage = styled.img`
  width: 100%;
  height: 100%;
  object-fit: cover;
`;

const FavoriteButton = styled.button`
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(255, 255, 255, 0.9);
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    background: white;
    transform: scale(1.1);
  }
`;

const CardContent = styled.div`
  padding: 1rem;
`;

const SellerInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
`;

const SellerAvatar = styled.img`
  width: 24px;
  height: 24px;
  border-radius: 50%;
`;

const SellerName = styled.span`
  font-size: 0.9rem;
  color: ${props => props.theme.text};
`;

const GigTitle = styled.h3`
  font-size: 1rem;
  font-weight: 600;
  color: ${props => props.theme.secondary};
  margin-bottom: 0.5rem;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
`;

const RatingContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-bottom: 0.5rem;
`;

const Rating = styled.div`
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.9rem;
`;

const StarIcon = styled(FiStar)`
  color: #ffb33e;
  fill: #ffb33e;
`;

const ReviewCount = styled.span`
  color: ${props => props.theme.text};
  font-size: 0.8rem;
`;

const PriceContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const Price = styled.div`
  font-size: 1.1rem;
  font-weight: 600;
  color: ${props => props.theme.secondary};

  &::before {
    content: 'From ';
    font-size: 0.8rem;
    font-weight: normal;
    color: ${props => props.theme.text};
  }
`;

const GigCard = ({ gig }) => {
  const [isFavorite, setIsFavorite] = React.useState(false);

  const handleFavorite = (e) => {
    e.preventDefault();
    setIsFavorite(!isFavorite);
  };

  return (
    <Link to={`/gig/${gig._id}`} style={{ textDecoration: 'none' }}>
      <Card>
        <ImageContainer>
          <GigImage 
            src={gig.images[0] || '/placeholder-gig.jpg'} 
            alt={gig.title}
          />
          <FavoriteButton onClick={handleFavorite}>
            <FiHeart color={isFavorite ? '#ff3838' : '#666'} fill={isFavorite ? '#ff3838' : 'none'} />
          </FavoriteButton>
        </ImageContainer>
        
        <CardContent>
          <SellerInfo>
            {gig.userId?.profilePicture ? (
              <SellerAvatar src={gig.userId.profilePicture} alt={gig.userId.username} />
            ) : (
              <div style={{ 
                width: 24, 
                height: 24, 
                borderRadius: '50%', 
                background: '#ddd',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '12px',
                color: '#666'
              }}>
                {gig.userId?.username?.charAt(0)?.toUpperCase() || 'U'}
              </div>
            )}
            <SellerName>{gig.userId?.username}</SellerName>
          </SellerInfo>
          
          <GigTitle>{gig.title}</GigTitle>
          
          <RatingContainer>
            <Rating>
              <StarIcon size={14} />
              <span>{gig.rating.toFixed(1)}</span>
            </Rating>
            <ReviewCount>({gig.totalReviews})</ReviewCount>
          </RatingContainer>
          
          <PriceContainer>
            <Price>${gig.pricing.basic.price}</Price>
          </PriceContainer>
        </CardContent>
      </Card>
    </Link>
  );
};

export default GigCard;