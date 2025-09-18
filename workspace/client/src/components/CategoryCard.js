import React from 'react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';

const Card = styled.div`
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 2rem;
  text-align: center;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  cursor: pointer;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  }
`;

const Icon = styled.div`
  font-size: 3rem;
  margin-bottom: 1rem;
`;

const Title = styled.h3`
  color: ${props => props.theme.secondary};
  margin-bottom: 0.5rem;
  font-size: 1.2rem;
`;

const Description = styled.p`
  color: ${props => props.theme.text};
  font-size: 0.9rem;
  margin-bottom: 1rem;
`;

const CategoryCard = ({ category }) => {
  return (
    <Link 
      to={`/search?category=${category.category}`} 
      style={{ textDecoration: 'none' }}
    >
      <Card>
        <Icon>{category.icon}</Icon>
        <Title>{category.name}</Title>
        <Description>{category.description}</Description>
      </Card>
    </Link>
  );
};

export default CategoryCard;