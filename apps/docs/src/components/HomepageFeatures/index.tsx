import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  icon: string;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Multi-modal AI Generation',
    icon: '🎨',
    description: (
      <>
        Generate and combine text, images, video, and audio using advanced AI models.
        Boards enables seamless multi-modal content creation for your projects.
      </>
    ),
  },
  {
    title: 'Collaborative Workspace',
    icon: '🤝',
    description: (
      <>
        Work together in real-time with your team. Share, edit, and organize ideas
        collaboratively within a unified workspace with drag-and-drop organization.
      </>
    ),
  },
  {
    title: 'Provider Integrations',
    icon: '🔌',
    description: (
      <>
        Connect with multiple AI providers and data sources. Boards integrates with
        Replicate, OpenAI, Fal.ai, and more to streamline your workflow.
      </>
    ),
  },
];

function Feature({title, icon, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <div className={styles.featureIcon}>{icon}</div>
      </div>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
