import React, { useState } from 'react';
import { useQuery } from 'react-query';
import axios from 'axios';
import styled from 'styled-components';
import { FiClock, FiCheckCircle, FiXCircle, FiMessageSquare } from 'react-icons/fi';

const OrdersContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
`;

const Title = styled.h1`
  color: ${props => props.theme.secondary};
  margin-bottom: 2rem;
`;

const TabContainer = styled.div`
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  border-bottom: 1px solid ${props => props.theme.border};
`;

const Tab = styled.button`
  padding: 1rem 2rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-size: 1rem;
  color: ${props => props.active ? props.theme.primary : props.theme.text};
  border-bottom-color: ${props => props.active ? props.theme.primary : 'transparent'};
  transition: all 0.3s ease;

  &:hover {
    color: ${props => props.theme.primary};
  }
`;

const OrdersGrid = styled.div`
  display: grid;
  gap: 1.5rem;
`;

const OrderCard = styled.div`
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 1rem;
  align-items: center;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;

const OrderInfo = styled.div`
  h3 {
    color: ${props => props.theme.secondary};
    margin-bottom: 0.5rem;
  }
`;

const OrderDetails = styled.div`
  display: flex;
  gap: 2rem;
  margin-top: 0.5rem;
  color: ${props => props.theme.text};
  font-size: 0.9rem;
`;

const StatusBadge = styled.div`
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 600;
  text-align: center;
  
  &.pending {
    background: #fff3cd;
    color: #856404;
  }
  
  &.in-progress {
    background: #d1ecf1;
    color: #0c5460;
  }
  
  &.delivered {
    background: #d4edda;
    color: #155724;
  }
  
  &.completed {
    background: #d4edda;
    color: #155724;
  }
  
  &.cancelled {
    background: #f8d7da;
    color: #721c24;
  }
`;

const ActionButton = styled.button`
  padding: 0.5rem 1rem;
  background: ${props => props.theme.primary};
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.3s ease;

  &:hover {
    background: ${props => props.theme.primaryHover};
  }
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 3rem;
  color: ${props => props.theme.text};
`;

const Orders = () => {
  const [activeTab, setActiveTab] = useState('buyer');

  const { data: orders, isLoading } = useQuery(
    ['orders', activeTab],
    () => axios.get(`/api/orders?type=${activeTab}`).then(res => res.data)
  );

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pending':
        return <FiClock />;
      case 'in-progress':
        return <FiClock />;
      case 'delivered':
        return <FiCheckCircle />;
      case 'completed':
        return <FiCheckCircle />;
      case 'cancelled':
        return <FiXCircle />;
      default:
        return <FiClock />;
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <OrdersContainer>
      <Title>Your Orders</Title>
      
      <TabContainer>
        <Tab 
          active={activeTab === 'buyer'} 
          onClick={() => setActiveTab('buyer')}
        >
          Buying
        </Tab>
        <Tab 
          active={activeTab === 'seller'} 
          onClick={() => setActiveTab('seller')}
        >
          Selling
        </Tab>
      </TabContainer>

      {isLoading ? (
        <div className="loading">Loading orders...</div>
      ) : orders?.length === 0 ? (
        <EmptyState>
          <h3>No orders yet</h3>
          <p>
            {activeTab === 'buyer' 
              ? 'Start exploring services and place your first order!' 
              : 'Create your first gig to start receiving orders!'}
          </p>
        </EmptyState>
      ) : (
        <OrdersGrid>
          {orders?.map(order => (
            <OrderCard key={order._id}>
              <OrderInfo>
                <h3>{order.title}</h3>
                <OrderDetails>
                  <span>
                    {activeTab === 'buyer' ? 'Seller' : 'Buyer'}: 
                    {activeTab === 'buyer' ? order.sellerId?.username : order.buyerId?.username}
                  </span>
                  <span>Package: {order.package}</span>
                  <span>Price: ${order.price}</span>
                  <span>Due: {formatDate(order.deliveryDate)}</span>
                </OrderDetails>
              </OrderInfo>
              
              <div style={{ textAlign: 'right' }}>
                <StatusBadge className={order.status}>
                  {getStatusIcon(order.status)} {order.status}
                </StatusBadge>
                <ActionButton style={{ marginTop: '0.5rem' }}>
                  <FiMessageSquare style={{ marginRight: '0.25rem' }} />
                  View Details
                </ActionButton>
              </div>
            </OrderCard>
          ))}
        </OrdersGrid>
      )}
    </OrdersContainer>
  );
};

export default Orders;