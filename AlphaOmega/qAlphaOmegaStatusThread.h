
#ifndef STRAEMTHREAD_H
#define STRAEMTHREAD_H

#include <QMutex>
#include <QSize>
#include <QThread>
#include <QWaitCondition>

#include "vtkMRMLScriptedModuleNode.h"


class qAlphaOmegaStatusThread : public QThread
{
  Q_OBJECT

public:

  qAlphaOmegaStatusThread(QObject *parent = nullptr);
  ~qAlphaOmegaStatusThread();

  static void SetParam(vtkMRMLScriptedModuleNode* p){param = p;};
  static vtkMRMLScriptedModuleNode* param;

signals:

  void connectionStatusModified(bool* deviceIsConnected);
  void distanceToTargetModified(float *distanceToTargetMiliM);

protected:

  void run() override;

private:

  float GetDistanceToTargetMiliM();

  QMutex Mutex;
  QWaitCondition Condition;
  bool Abort = false;

};

#endif