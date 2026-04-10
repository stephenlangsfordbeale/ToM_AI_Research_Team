targetScope = 'resourceGroup'

@description('Location for resources')
param location string = resourceGroup().location

@description('Azure ML workspace name')
param mlWorkspaceName string = 'mlw-tom-coord'

@description('Azure Storage account name for the AML workspace')
param storageAccountName string = 'sttomcoord${uniqueString(resourceGroup().id)}'

@description('Azure Key Vault name for the AML workspace')
param keyVaultName string = 'kvtom${uniqueString(resourceGroup().id)}'

@description('Application Insights name for the AML workspace')
param appInsightsName string = 'appitom${uniqueString(resourceGroup().id)}'

@description('Azure Container Registry name')
param acrName string = 'acrtomcoord${uniqueString(resourceGroup().id)}'

@description('AML compute cluster name')
param computeClusterName string = 'cpu-cluster'

@description('AML compute VM size')
param computeVmSize string = 'STANDARD_DS3_V2'

@description('AML compute minimum node count')
param computeMinInstances int = 0

@description('AML compute maximum node count')
param computeMaxInstances int = 4

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    accessPolicies: []
    enabledForDeployment: false
    enabledForTemplateDeployment: false
    enabledForDiskEncryption: false
    enableRbacAuthorization: true
    enableSoftDelete: true
    enablePurgeProtection: true
    publicNetworkAccess: 'Enabled'
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: ''
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
    policies: {
      quarantinePolicy: {
        status: 'disabled'
      }
      trustPolicy: {
        type: 'Notary'
        status: 'disabled'
      }
    }
  }
}

resource mlWorkspace 'Microsoft.MachineLearningServices/workspaces@2024-04-01-preview' = {
  name: mlWorkspaceName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  properties: {
    storageAccount: storageAccount.id
    keyVault: keyVault.id
    applicationInsights: appInsights.id
    containerRegistry: acr.id
    publicNetworkAccess: 'Enabled'
  }
}

resource amlCompute 'Microsoft.MachineLearningServices/workspaces/computes@2024-04-01-preview' = {
  parent: mlWorkspace
  name: computeClusterName
  location: location
  properties: {
    computeType: 'AmlCompute'
    properties: {
      vmSize: computeVmSize
      enableNodePublicIp: false
      scaleSettings: {
        minNodeCount: computeMinInstances
        maxNodeCount: computeMaxInstances
        nodeIdleTimeBeforeScaleDown: 'PT300S'
      }
    }
  }
}

output workspaceId string = mlWorkspace.id
output workspaceName string = mlWorkspace.name
output storageAccountId string = storageAccount.id
output keyVaultId string = keyVault.id
output appInsightsId string = appInsights.id
output acrId string = acr.id
output acrLoginServer string = acr.properties.loginServer
output amlComputeName string = computeClusterName
