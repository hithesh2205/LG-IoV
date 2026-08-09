import {
  Database,
  Settings,
  Cpu,
  Network,
  Car,
  Brain,
  GraduationCap,
  Lock,
  Cloud,
  Shield,
  Send,
  Radio,
} from 'lucide-react';

// Node position constants  
const COL_LEFT = 200;
const COL_MID = 500;
const COL_RIGHT = 800;
const START_Y = 30;
const ROW_GAP = 120;

export const nodeData = [
  // =============== TOP PIPELINE ===============
  {
    id: 'datasets',
    type: 'archNode',
    position: { x: COL_MID, y: START_Y },
    data: {
      label: 'Datasets',
      icon: 'Database',
      color: 'blue',
      module: 'datasets',
      description: 'Car Hacking, VeReMi, CICIDS2017, CANVTC',
    },
  },
  {
    id: 'preprocessing',
    type: 'archNode',
    position: { x: COL_MID, y: START_Y + ROW_GAP },
    data: {
      label: 'Data Preprocessing',
      icon: 'Settings',
      color: 'blue',
      module: 'preprocessing',
      description: 'Cleaning, Normalization, Encoding',
    },
  },
  {
    id: 'features',
    type: 'archNode',
    position: { x: COL_MID, y: START_Y + ROW_GAP * 2 },
    data: {
      label: 'Feature Engineering',
      icon: 'Cpu',
      color: 'cyan',
      module: 'features',
      description: '46 Engineered Features',
    },
  },
  {
    id: 'distribution',
    type: 'archNode',
    position: { x: COL_MID, y: START_Y + ROW_GAP * 3 },
    data: {
      label: 'Non-IID Client Distribution',
      icon: 'Network',
      color: 'cyan',
      module: 'distribution',
      description: 'Dirichlet α-based Partitioning',
    },
  },

  // =============== VEHICLE CLIENTS ===============
  {
    id: 'vehicle-a',
    type: 'archNode',
    position: { x: COL_LEFT, y: START_Y + ROW_GAP * 4.3 },
    data: {
      label: 'Vehicle A',
      icon: 'Car',
      color: 'blue',
      module: null,
      description: 'FL Client 1',
    },
  },
  {
    id: 'vehicle-b',
    type: 'archNode',
    position: { x: COL_MID, y: START_Y + ROW_GAP * 4.3 },
    data: {
      label: 'Vehicle B',
      icon: 'Car',
      color: 'blue',
      module: null,
      description: 'FL Client 2',
    },
  },
  {
    id: 'vehicle-c',
    type: 'archNode',
    position: { x: COL_RIGHT, y: START_Y + ROW_GAP * 4.3 },
    data: {
      label: 'Vehicle C',
      icon: 'Car',
      color: 'blue',
      module: null,
      description: 'FL Client 3',
    },
  },

  // =============== MAMKANFORMER ===============
  {
    id: 'mamba-a',
    type: 'archNode',
    position: { x: COL_LEFT, y: START_Y + ROW_GAP * 5.5 },
    data: {
      label: 'MamKANFormer',
      icon: 'Brain',
      color: 'purple',
      module: 'mamkanformer',
      description: 'Mamba + KAN + Transformer',
    },
  },
  {
    id: 'mamba-b',
    type: 'archNode',
    position: { x: COL_MID, y: START_Y + ROW_GAP * 5.5 },
    data: {
      label: 'MamKANFormer',
      icon: 'Brain',
      color: 'purple',
      module: 'mamkanformer',
      description: 'Mamba + KAN + Transformer',
    },
  },
  {
    id: 'mamba-c',
    type: 'archNode',
    position: { x: COL_RIGHT, y: START_Y + ROW_GAP * 5.5 },
    data: {
      label: 'MamKANFormer',
      icon: 'Brain',
      color: 'purple',
      module: 'mamkanformer',
      description: 'Mamba + KAN + Transformer',
    },
  },

  // =============== LOCAL TRAINING ===============
  {
    id: 'train-a',
    type: 'archNode',
    position: { x: COL_LEFT, y: START_Y + ROW_GAP * 6.7 },
    data: {
      label: 'Local Training',
      icon: 'GraduationCap',
      color: 'cyan',
      module: null,
      description: 'SGD / Adam Optimization',
    },
  },
  {
    id: 'train-b',
    type: 'archNode',
    position: { x: COL_MID, y: START_Y + ROW_GAP * 6.7 },
    data: {
      label: 'Local Training',
      icon: 'GraduationCap',
      color: 'cyan',
      module: null,
      description: 'SGD / Adam Optimization',
    },
  },
  {
    id: 'train-c',
    type: 'archNode',
    position: { x: COL_RIGHT, y: START_Y + ROW_GAP * 6.7 },
    data: {
      label: 'Local Training',
      icon: 'GraduationCap',
      color: 'cyan',
      module: null,
      description: 'SGD / Adam Optimization',
    },
  },

  // =============== CKKS ENCRYPTION ===============
  {
    id: 'ckks-a',
    type: 'archNode',
    position: { x: COL_LEFT, y: START_Y + ROW_GAP * 7.9 },
    data: {
      label: 'CKKS Full FHE',
      icon: 'Lock',
      color: 'purple',
      module: 'ckks',
      description: 'Fully Homomorphic Encryption',
    },
  },
  {
    id: 'ckks-b',
    type: 'archNode',
    position: { x: COL_MID, y: START_Y + ROW_GAP * 7.9 },
    data: {
      label: 'CKKS Full FHE',
      icon: 'Lock',
      color: 'purple',
      module: 'ckks',
      description: 'Fully Homomorphic Encryption',
    },
  },
  {
    id: 'ckks-c',
    type: 'archNode',
    position: { x: COL_RIGHT, y: START_Y + ROW_GAP * 7.9 },
    data: {
      label: 'CKKS Full FHE',
      icon: 'Lock',
      color: 'purple',
      module: 'ckks',
      description: 'Fully Homomorphic Encryption',
    },
  },

  // =============== CLOUD SERVER ===============
  {
    id: 'cloud',
    type: 'archNode',
    position: { x: COL_MID, y: START_Y + ROW_GAP * 9.3 },
    data: {
      label: 'Federated Cloud Server',
      icon: 'Cloud',
      color: 'blue',
      module: 'cloud',
      description: 'Aggregation, Multi-Krum, TOPSIS',
      large: true,
    },
  },

  // =============== BROADCAST ===============
  {
    id: 'broadcast',
    type: 'archNode',
    position: { x: COL_MID, y: START_Y + ROW_GAP * 10.5 },
    data: {
      label: 'Broadcast Global Model',
      icon: 'Send',
      color: 'cyan',
      module: null,
      description: 'Distribute Updated Weights',
    },
  },

  // =============== RECEIVING VEHICLES ===============
  {
    id: 'recv-a',
    type: 'archNode',
    position: { x: COL_LEFT, y: START_Y + ROW_GAP * 11.7 },
    data: {
      label: 'Vehicle A',
      icon: 'Car',
      color: 'blue',
      module: null,
      description: 'Updated Model',
    },
  },
  {
    id: 'recv-b',
    type: 'archNode',
    position: { x: COL_MID, y: START_Y + ROW_GAP * 11.7 },
    data: {
      label: 'Vehicle B',
      icon: 'Car',
      color: 'blue',
      module: null,
      description: 'Updated Model',
    },
  },
  {
    id: 'recv-c',
    type: 'archNode',
    position: { x: COL_RIGHT, y: START_Y + ROW_GAP * 11.7 },
    data: {
      label: 'Vehicle C',
      icon: 'Car',
      color: 'blue',
      module: null,
      description: 'Updated Model',
    },
  },

  // =============== IDS ===============
  {
    id: 'ids-a',
    type: 'archNode',
    position: { x: COL_LEFT, y: START_Y + ROW_GAP * 12.9 },
    data: {
      label: 'IDS',
      icon: 'Shield',
      color: 'purple',
      module: 'ids',
      description: 'Intrusion Detection System',
    },
  },
  {
    id: 'ids-b',
    type: 'archNode',
    position: { x: COL_MID, y: START_Y + ROW_GAP * 12.9 },
    data: {
      label: 'IDS',
      icon: 'Shield',
      color: 'purple',
      module: 'ids',
      description: 'Intrusion Detection System',
    },
  },
  {
    id: 'ids-c',
    type: 'archNode',
    position: { x: COL_RIGHT, y: START_Y + ROW_GAP * 12.9 },
    data: {
      label: 'IDS',
      icon: 'Shield',
      color: 'purple',
      module: 'ids',
      description: 'Intrusion Detection System',
    },
  },
];

export const iconMap = {
  Database,
  Settings,
  Cpu,
  Network,
  Car,
  Brain,
  GraduationCap,
  Lock,
  Cloud,
  Shield,
  Send,
  Radio,
};
